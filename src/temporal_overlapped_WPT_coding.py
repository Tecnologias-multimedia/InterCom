#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Overlapping chunks (WPT).'''

import numpy as np
import sounddevice as sd
import pywt
import logging
import minimal

from stereo_MST_coding_32 import Stereo_MST_Coding_32 as Stereo_Coding
from temporal_no_overlapped_WPT_coding import Temporal_No_Overlapped_WPT
from temporal_no_overlapped_WPT_coding import Temporal_No_Overlapped_WPT__verbose

#from DEFLATE_byteplanes3 import DEFLATE_BytePlanes3 as EC

class Temporal_Overlapped_WPT(Temporal_No_Overlapped_WPT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.number_of_overlapped_samples = self.max_filters_length * (1 << self.DWT_levels)
        logging.info(f"number of overlapped samples = {self.number_of_overlapped_samples}")
        logging.info(f"extended chunk size = {minimal.args.frames_per_chunk + self.number_of_overlapped_samples*2}")

        # Structure to keep chunks during encoding
        self.e_chunk_list = []
        self.e_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.e_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.e_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))

        # Structure to keep chunks during decoding
        self.d_chunk_list = []
        self.d_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.d_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.d_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))

    def analyze(self, chunk):
        chunk = Stereo_Coding.analyze(self, chunk)
        self.e_chunk_list.pop(0)
        self.e_chunk_list.append(chunk)
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk
        extended_chunk = np.concatenate([self.e_chunk_list[0][-o:], self.e_chunk_list[1], self.e_chunk_list[2][:o]])
        packet_data_flat = np.empty((fpc, chunk.shape[1]), dtype=np.int32)

        for c in range(minimal.args.number_of_channels):
            wp = pywt.WaveletPacket(data=extended_chunk[:, c], wavelet=self.wavelet, mode='per', maxlevel=self.DWT_levels)
            nodes = wp.get_level(self.DWT_levels, 'freq')
            col_data = []
            for i, node in enumerate(nodes):
                data = node.data
                #q = self.quantization_steps[i] if i < len(self.quantization_steps) else 1
                #data = data / q
                offset = o // (2**self.DWT_levels)
                sliced = data[offset:-offset] if offset > 0 else data
                col_data.append(sliced)
            c_col = np.concatenate(col_data)
            packet_data_flat[:, c] = np.rint(c_col)

        return packet_data_flat.astype(np.int32)

    def synthesize(self, WPT_chunk):
        self.d_chunk_list.pop(0)
        self.d_chunk_list.append(WPT_chunk)
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk
        num_bands = 2**self.DWT_levels
        band_len = fpc // num_bands
        offset = o // num_bands
        reconstructed_chunk = np.empty((fpc, WPT_chunk.shape[1]), dtype=np.float32)

        for c in range(minimal.args.number_of_channels):
            coeffs = []
            prev, curr, next = [x[:, c] for x in self.d_chunk_list]
            for b in range(num_bands):
                s_start, s_end = b*band_len, (b+1)*band_len
                p_tail = prev[s_start:s_end][-offset:] if offset > 0 else []
                n_head = next[s_start:s_end][:offset] if offset > 0 else []
                ext_band = np.concatenate([p_tail, curr[s_start:s_end], n_head])
                #q = self.quantization_steps[b] if b < len(self.quantization_steps) else 1
                coeffs.append(ext_band)

            dummy_len = fpc + 2*o
            wp = pywt.WaveletPacket(data=np.zeros(dummy_len), wavelet=self.wavelet, mode='per', maxlevel=self.DWT_levels)
            nodes = wp.get_level(self.DWT_levels, 'freq')
            for i, node in enumerate(nodes):
                if True:#if i < len(coeffs):
                     tgt = len(node.data); src = coeffs[i]
                     node.data = src[:tgt] if len(src) >= tgt else np.pad(src, (0, tgt - len(src)))
            rec = wp.reconstruct(update=False)
            rec_final = rec[o:-o] if o > 0 else rec
            reconstructed_chunk[:, c] = rec_final[:fpc]

        #if minimal.args.number_of_channels == 1 and chunk_WP.shape[1] == 2:
        #     return np.clip(reconstructed_chunk[:, 0].reshape(-1, 1), -32768, 32767)
        #chunk = np.clip(reconstructed_chunk, -32768, 32767)
        chunk = Stereo_Coding.synthesize(self, reconstructed_chunk)
        return chunk

    def __pack(self, chunk_number, chunk):
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

    def __unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = EC.unpack(self, packed_chunk)
        # Dequantize
        WPT_chunk = []
        for c in range(minimal.args.number_of_channels):
            WPT_channel = self.fill_wavelet_packet(analyzed_chunk[:, c], self.wavelet, "per", self.DWT_levels)
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

class Temporal_Overlapped_WPT__verbose(Temporal_Overlapped_WPT, Temporal_No_Overlapped_WPT__verbose):
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
        intercom = Temporal_Overlapped_WPT__verbose()
    else:
        intercom = Temporal_Overlapped_WPT()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received.")
    finally:
        intercom.print_final_averages()
