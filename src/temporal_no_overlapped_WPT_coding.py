#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""Removes spatial (inter-channel) and temporal (intra-channel) redundancy using the WPT (Wavelet Packet Transform), without chunk overlapping."""

import numpy as np
import sounddevice as sd
import pywt
import logging
import minimal
from stereo_MST_coding_32 import Stereo_MST_Coding_32 as Stereo_Coding
from DEFLATE_byteplanes3 import DEFLATE_BytePlanes3 as EC
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT

class Temporal_No_Overlapped_WPT(Temporal_No_Overlapped_DWT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.number_of_subbands = 2**self.DWT_levels
        logging.info(f"number of subbands = {self.number_of_subbands}")
        self.subbands_length = minimal.args.frames_per_chunk//self.number_of_subbands
        logging.info(f"subbands_length (number of coefficients per subband) = {self.subbands_length}")

    def analyze_in_time(self, chunk):
        decomposition = np.empty_like(chunk)
        for c in range(chunk.shape[1]):
            WPS = pywt.WaveletPacket(data=chunk[:, c], wavelet=self.wavelet, maxlevel=self.DWT_levels, mode="per")
            decomposition[:, c] = np.concatenate([node.data for node in WPS.get_level(WPS.maxlevel, order="freq")])
        return decomposition
        
    def synthesize_in_time(self, decomposition):
        chunk = np.empty_like(decomposition)
        for c in range(decomposition.shape[1]):
            WPT_channel = self.fill_wavelet_packet(decomposition[:, c], self.wavelet, "per")
            chunk[:, c] = WPT_channel.reconstruct(update=False)
        return chunk

    def fill_wavelet_packet(self, data, wavelet, mode):
        # Create a dummy WaveletPacket to get the structure.
        dummy_wp = pywt.WaveletPacket(np.zeros_like(data), wavelet, mode, maxlevel=self.DWT_levels)

        # Calculate the length of each node's data.
        node_length = len(data) // self.number_of_subbands

        # Traverse the tree and fill the nodes with data.
        current_index = 0
        for node in dummy_wp.get_level(self.DWT_levels, order="freq"):
            node.data = data[current_index:current_index + node_length]
            current_index += node_length

        return dummy_wp

from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT__verbose

class Temporal_No_Overlapped_WPT__verbose(Temporal_No_Overlapped_WPT, Temporal_No_Overlapped_DWT__verbose):
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
        intercom = Temporal_No_Overlapped_WPT__verbose()
    else:
        intercom = Temporal_No_Overlapped_WPT()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received.")
    finally:
        intercom.print_final_averages()
