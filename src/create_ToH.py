#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Create a custom (personal) ToH.
U N F I N I S H E D !
"""

import numpy as np
import sounddevice as sd
import pywt
import logging
import minimal
from dyadic_ToH import Threshold, Threshold__verbose
from stereo_MST_coding_16 import Stereo_MST_Coding_16 as Stereo_Coding
from DEFLATE_byteplanes3 import DEFLATE_BytePlanes3 as EC

class AdvancedThreshold(Threshold):

    def __init__(self):
        """
        Initialize the AdvancedThreshold class with Wavelet Packets and levels.
        """
        super().__init__()

        self.args = minimal.args
        self.WPT_levels = 6
        print(self.WPT_levels)

        if self.args.custom_toh:
            logging.info("Using custom ToH.")
            self.quantization_steps = self.calculate_custom_qss()
        else:
            logging.info("Using standard ToH.")
            self.quantization_steps = self.calculate_quantization_steps(max_q=64)

    def calculate_quantization_steps(self, max_q):
        """
        Calculate Quantization Step Sizes (QSS) for each subband based on Wavelet Packet decomposition.
        """

        def calc(f):
            return 3.64 * (f / 1000) ** (-0.8) - 6.5 * np.exp(-0.6 * (f / 1000 - 3.3) ** 2) + 1e-3 * (f / 1000) ** 4

        f = 22050
        subbands = 2 ** self.dwt_levels
        frequencies = [(f / subbands) * (i + 0.5) for i in range(subbands)]

        spl_values = [calc(f) for f in frequencies]
        min_SPL = min(spl_values)
        max_SPL = max(spl_values)
        quantization_steps = [
            round((spl - min_SPL) / (max_SPL - min_SPL) * (max_q - 1) + 1) * minimal.args.minimal_quantization_step_size
            #round((spl - min_SPL) / (max_SPL - min_SPL) * (max_q - 1) + 1) * 10
            for spl in spl_values
        ]
        #quantization_steps = [1 for spl in spl_values]
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
            for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel, order="freq"):
                node.data = (node.data / self.quantization_steps[i]).astype(np.int32)
                i += 1
            analyzed_chunk[:, c] = np.concatenate([node.data for node in WPT_chunk[c].get_level(WPT_chunk[c].maxlevel, order="freq")])
        packed_chunk = EC.pack(self, chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = EC.unpack(self, packed_chunk)
        # Dequantize
        WPT_chunk = []
        for c in range(minimal.args.number_of_channels):
            WPT_channel = self.fill_wavelet_packet(analyzed_chunk[:, c], self.wavelet, "per", self.dwt_levels)
            i = 0
            for node in WPT_channel.get_level(WPT_channel.maxlevel, order="freq"):
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
        for node in dummy_wp.get_level(levels, order="freq"):
        #for node in dummy_wp.get_level(levels):
            node.data = data[current_index:current_index + node_length]
            current_index += node_length

        return dummy_wp

    def calculate_custom_qss(self):
        logging.info("Custom ToH setup started. Adjusting QSS for each subband...")
        wp = pywt.WaveletPacket(data=np.zeros(self.args.frames_per_chunk), wavelet='db5', mode='symmetric')

        # Validate DWT levels
        max_dwt_levels = pywt.dwt_max_level(len(wp.data), pywt.Wavelet('db5').dec_len)
        self.dwt_levels = min(self.dwt_levels, max_dwt_levels)
        logging.info(f"Using DWT levels: {self.dwt_levels}")

        qss = [0] * (2 ** self.dwt_levels)

        for i, node in enumerate(wp.get_level(self.dwt_levels, order="freq")):
        #for i, node in enumerate(wp.get_level(self.dwt_levels)):
            logging.info(f"Adjusting QSS for subband {i + 1}/{len(qss)}.")
            frequency = 1000
            amplitude = 0.5
            no_change_count = 0

            while no_change_count < 3:
                test_tone = self.generate_test_tone(frequency, amplitude)
                self.play_test_chunk(test_tone)

                response = input("Can you perceive the tone? (y/n): ").strip().lower()
                if response == 'y':
                    amplitude = max(0.05, amplitude - 0.05)
                else:
                    no_change_count += 1
                    amplitude = min(1.0, amplitude + 0.05)

                logging.info(f"Adjusted amplitude: {amplitude}")

            qss[i] = amplitude
            logging.info(f"Final QSS for subband {i + 1}: {qss[i]}")

        logging.info("Custom ToH setup complete.")
        return qss

    def generate_test_tone(self, frequency, amplitude):
        """
        Generate a test tone for a given frequency and amplitude.
        """
        t = np.arange(0, self.args.frames_per_chunk) / self.args.frames_per_second
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        tone = np.clip(tone, -1, 1) * 0.8 * np.iinfo(np.int16).max  # Adjust scaling
        logging.debug(f"Generated test tone at {frequency} Hz with amplitude {amplitude}")
        return tone.astype(np.int16)

    def output_audio(self, chunk):
        """
        Outputs a chunk of audio to the default audio device.
        """
        try:
            samplerate = self.args.frames_per_second
            logging.info(f"Playing audio chunk at samplerate: {samplerate}")
            sd.play(chunk, samplerate=samplerate)
            sd.wait()  # Wait for playback to finish
        except Exception as e:
            logging.error(f"Error during audio playback: {e}")

    def play_test_chunk(self, tone):
        """
        Play a test tone chunk.
        """
        logging.info(f"Playing test tone with max value: {np.max(tone)}")
        sd.play(tone, samplerate=self.args.frames_per_second)
        sd.wait()

class AdvancedThreshold__verbose(AdvancedThreshold, Threshold__verbose):
    def __init__(self):
        """
        Initialize the verbose version of AdvancedThreshold.
        """
        AdvancedThreshold.__init__(self)
        Threshold__verbose.__init__(self)


try:
    import argcomplete
except ImportError:
    logging.warning("argcomplete not available.")

if __name__ == "__main__":
    minimal.parser.description = __doc__

    minimal.parser.add_argument(
        "--custom-toh", action="store_true",
        help="Use custom ToH curves determined interactively."
    )

    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working.")

    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = AdvancedThreshold__verbose()
    else:
        intercom = AdvancedThreshold()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received.")
    finally:
        intercom.print_final_averages()
