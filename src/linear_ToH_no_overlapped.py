#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Using Wavelet Packets a for better frequency resolution. Chunks are not overlapped.
"""

import numpy as np
import sounddevice as sd
import pywt
import logging
import minimal
from dyadic_ToH import Dyadic_ToH, Dyadic_ToH__verbose
from stereo_MST_coding_16 import Stereo_MST_Coding_16 as Stereo_Coding
from DEFLATE_byteplanes3 import DEFLATE_BytePlanes3 as EC

class Linear_ToH_NO(Dyadic_ToH):

    def __init__(self):
        super().__init__()
        self.quantization_steps = Linear_ToH_NO.calculate_quantization_steps(self, max_expected_q=1024)

    def calculate_quantization_steps(self, max_expected_q):
        """
        Calculate Quantization Step Sizes (QSS) for each subband based on Wavelet Packet decomposition.
        """

        def print_shape(start_freq=50, end_freq=22050, num_points=2**self.dwt_levels, max_width=100):
            """
            Prints a text-based representation of the shape described by the calc function,
            including a first column with the frequency.

            Args:
                start_freq (int): Starting frequency.
                end_freq (int): Ending frequency.
                num_points (int): Number of frequency points to evaluate.
                max_width (int): Maximum width of the printed shape.
            """

            frequencies = np.linspace(start_freq, end_freq, num_points)
            values = np.array([self.calc(f) for f in frequencies])

            # Normalize values to the range [0, 1]
            min_val = np.min(values)
            max_val = np.max(values)
            normalized_values = (values - min_val) / (max_val - min_val)

            i = 1
            for freq, val in zip(frequencies, normalized_values):
                num_stars = int(val * max_width)
                print(f"{i:3} | {freq:5.0f} | {num_stars+1:2} | {'*' * (num_stars+1)}")
                i += 1


        f = 22050
        subbands = 2 ** self.dwt_levels
        print_shape(end_freq=f, num_points = subbands)
        frequencies = [(f / subbands) * (i + 0.5) for i in range(subbands)]
        SPL_values = np.array([self.calc(f) for f in frequencies])
        min_SPL = min(SPL_values)
        max_SPL = max(SPL_values)
        quantization_steps = np.array([
            round(((SPL - min_SPL) / (max_SPL - min_SPL) * (max_expected_q - 1) + 1) * minimal.args.minimal_quantization_step_size)
            for SPL in SPL_values
        ])
        logging.info(f"Quantization steps: {quantization_steps}")
        return quantization_steps

    def analyze(self, chunk):
        chunk = Stereo_Coding.analyze(self, chunk)
        WPT_chunk = []
        for c in range(minimal.args.number_of_channels):
            WPT_chunk.append(pywt.WaveletPacket(data=chunk[:, c], wavelet=self.wavelet, maxlevel=self.dwt_levels, mode="per"))

        return WPT_chunk # A list of two Wavelet Packet Transform
                         # structures (see
                         # https://pywavelets.readthedocs.io/en/latest/ref/wavelet-packets.html#pywt.WaveletPacket)

    def synthesize(self, WPT_chunk):
        chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            chunk[:, c] = WPT_chunk[c].reconstruct(update=False)
        chunk = Stereo_Coding.synthesize(self, chunk)
        return chunk

    def pack(self, chunk_number, chunk):
        WPT_chunk = self.analyze(chunk)
        # Quantize subbands
        analyzed_chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels))
        for c in range(minimal.args.number_of_channels):
            i = 0
            #for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel, order="freq"):
            for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel, order="natural"):
            #for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel):
                node.data = (node.data / self.quantization_steps[i]).astype(np.int32)
                i += 1
            #analyzed_chunk[:, c] = np.concatenate([node.data for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel, order="freq")])
            analyzed_chunk[:, c] = np.concatenate([node.data for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel, order="natural")])
            #analyzed_chunk[:, c] = np.concatenate([node.data for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel)])
        packed_chunk = EC.pack(self, chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = EC.unpack(self, packed_chunk)
        # Dequantize
        WPT_chunk = []
        for c in range(minimal.args.number_of_channels):
            WPT_channel = self.fill_wavelet_packet(analyzed_chunk[:, c], self.wavelet, "per", self.dwt_levels)
            i = 0
            #for node in WPT_channel.get_level(WPT_channel.maxlevel, order="freq"):
            for node in WPT_channel.get_level(WPT_channel.maxlevel, order="natural"):
            #for node in WPT_channel.get_level(WPT_channel.maxlevel):
                node.data = node.data * self.quantization_steps[i]
                i += 1
            WPT_chunk.append(WPT_channel)
        chunk = self.synthesize(WPT_chunk)
        return chunk_number, chunk

    def fill_wavelet_packet(self, data, wavelet, mode, levels):
        """
        Fills a WaveletPacket structure with data from a NumPy array.

        Args:
            data (np.ndarray): NumPy array of wavelet packet coefficients.
            wavelet (str): Wavelet name (e.g., 'db4').
            mode (str): Boundary extension mode (e.g., 'symmetric').
            levels (int): Number of decomposition levels.

        Returns:
            pywt.WaveletPacket: Filled WaveletPacket object.
        """

        # Create a dummy WaveletPacket to get the structure.
        dummy_wp = pywt.WaveletPacket(np.zeros_like(data), wavelet, mode, maxlevel=levels)

        # Get the number of nodes at the finest level
        num_nodes_at_level = 2**levels

        # Calculate the length of each node's data.
        node_length = len(data) // num_nodes_at_level

        # Traverse the tree and fill the nodes with data.
        current_index = 0
        #for node in dummy_wp.get_level(levels, order="freq"):
        for node in dummy_wp.get_level(levels, order="natural"):
        #for node in dummy_wp.get_level(levels):
            node.data = data[current_index:current_index + node_length]
            current_index += node_length

        return dummy_wp

class Linear_ToH_NO__verbose(Linear_ToH_NO, Dyadic_ToH__verbose):
    pass

try:
    import argcomplete
except ImportError:
    logging.warning("argcomplete not available.")

if __name__ == "__main__":
    minimal.parser.description = __doc__

    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working.")

    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = Linear_ToH_NO__verbose()
    else:
        intercom = Linear_ToH_NO()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received.")
    finally:
        intercom.print_final_averages()
