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

        self.e_chunk_list = [np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32) for _ in range(3)]
        self.d_chunk_list = [np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32) for _ in range(3)]

        self.number_of_subbands = 2**self.DWT_levels
        logging.info(f"number of subbands = {self.number_of_subbands}")
        self.subbands_length = minimal.args.frames_per_chunk // self.number_of_subbands
        logging.info(f"subbands length = {self.subbands_length}")
        self.offset = self.number_of_overlapped_samples // self.number_of_subbands

    def analyze(self, chunk):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk

        # Input C_i+1 (and move the previous chunks)
        self.e_chunk_list.pop(0)
        MST_chunk = Stereo_Coding.analyze(self, chunk)
        self.e_chunk_list.append(MST_chunk)

        # Build extended chunk
        extended_MST_chunk = np.concatenate(
            (self.e_chunk_list[0][-o:],
             self.e_chunk_list[1],
             self.e_chunk_list[2][:o])
        )

        def WPT_and_extract(extended_chunk):
            WPT_chunk = np.empty((fpc, minimal.args.number_of_channels), dtype=np.int32)
            for c in range(minimal.args.number_of_channels):
                packet_decomp = pywt.WaveletPacket(
                    data=extended_chunk[:, c],
                    wavelet=self.wavelet,
                    mode='per',
                    maxlevel=self.DWT_levels)
                nodes = packet_decomp.get_level(self.DWT_levels, 'freq')
                col_data = []
                for i, node in enumerate(nodes):
                    data = node.data
                    slice_ = data[self.offset:-self.offset]
                    col_data.append(slice_)
                c_col = np.concatenate(col_data)
                WPT_chunk[:, c] = c_col
            return WPT_chunk
        WPT_chunk = WPT_and_extract(extended_MST_chunk)
        return WPT_chunk

    def analyze(self, chunk):
        return chunk

    def synthesize(self, WPT_chunk):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk
        self.d_chunk_list.pop(0)
        self.d_chunk_list.append(WPT_chunk)
        
        MST_chunk = np.empty((fpc, WPT_chunk.shape[1]), dtype=np.float32)

        for c in range(minimal.args.number_of_channels):
            coeffs = []
            prev, curr, next = [x[:, c] for x in self.d_chunk_list]
            for b in range(self.number_of_subbands):
                s_start, s_end = b*self.subbands_length, (b+1)*self.subbands_length
                p_tail = prev[s_start:s_end][-self.offset:]
                n_head = next[s_start:s_end][:self.offset]
                ext_band = np.concatenate([p_tail, curr[s_start:s_end], n_head])
                coeffs.append(ext_band)
            dummy_len = fpc + 2*o
            wp = pywt.WaveletPacket(
                data=np.zeros(dummy_len),
                wavelet=self.wavelet,
                mode='per',
                maxlevel=self.DWT_levels)
            nodes = wp.get_level(self.DWT_levels, 'freq')
            for i, node in enumerate(nodes):
                tgt = len(node.data)
                src = coeffs[i]
                node.data = src[:tgt]
            rec = wp.reconstruct(update=False)
            rec_final = rec[o:-o]
            MST_chunk[:, c] = rec_final[:fpc]

        chunk = Stereo_Coding.synthesize(self, MST_chunk)
        return chunk

    def synthesize(self, chunk):
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
