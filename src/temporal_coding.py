#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Base class. No DWT.'''

import numpy as np
import pywt  # pip install pywavelets
import minimal
from stereo_coding_32 import Stereo_Coding_32 as Stereo_Coding
import logging

minimal.parser.add_argument("-w", "--wavelet_name", type=str, default="db5", help="Name of the wavelet")
minimal.parser.add_argument("-e", "--levels", type=str, help="Number of levels of DWT")

class Temporal_Coding(Stereo_Coding):
    pass # <-----------------------------------------------------
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

        self.wavelet = pywt.Wavelet(minimal.args.wavelet_name)
        
        # Default dwt_levels is based on the length of the chunk and the length of the filter
        self.max_filters_length = max(self.wavelet.dec_len, self.wavelet.rec_len)
        self.dwt_levels = pywt.dwt_max_level(data_len=minimal.args.frames_per_chunk//4, filter_len=self.max_filters_length)
        if minimal.args.levels:
            self.dwt_levels = int(minimal.args.levels)

        # Structure used during the decoding
        zero_array = np.zeros(shape=minimal.args.frames_per_chunk)
        coeffs = pywt.wavedec(zero_array, wavelet=self.wavelet, level=self.dwt_levels, mode="per")
        self.slices = pywt.coeffs_to_array(coeffs)[1]

        logging.info(f"wavelet name = {minimal.args.wavelet_name}")
        logging.info(f"analysis filters's length = {self.wavelet.dec_len}")
        logging.info(f"synthesis filters's length = {self.wavelet.rec_len}")
        logging.info(f"DWT levels = {self.dwt_levels}")

    def analyze(self, chunk):
        analyzed_chunk = super().analyze(chunk)
        #analyzed_chunk = Stereo_Coding.analyze(self, chunk)
        return analyzed_chunk

    def synthesize(self, DWT_chunk):
        chunk = super().synthesize(DWT_chunk)
        #chunk = Stereo_Coding.synthesize(self, DWT_chunk)
        return chunk

'''
    def pack(self, chunk_number, chunk):
        analyzed_chunk = self.analyze(chunk)
        #packed_chunk = super().pack(chunk_number, analyzed_chunk)
        packed_chunk = Stereo_Coding.pack(self, chunk_number, analyzed_chunk)
        return packed_chunk
    def unpack(self, packed_chunk):
        #chunk_number, analyzed_chunk = super().unpack(packed_chunk)
        chunk_number, analyzed_chunk = Stereo_Coding.unpack(self, packed_chunk)
        chunk = self.synthesize(analyzed_chunk)
        return chunk_number, chunk
'''
from stereo_coding_32 import Stereo_Coding_32__verbose as Stereo_Coding__verbose

class Temporal_Coding__verbose(Temporal_Coding, Stereo_Coding__verbose):
    pass
'''
    def __init__(self):
        super().__init__()

    def analyze(self, chunk):
        analyzed_chunk = Temporal_Coding.analyze(self, chunk)
        self.LH_chunks_in_the_cycle.append(analyzed_chunk)
        return analyzed_chunk
'''

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Temporal_Coding__verbose()
    else:
        intercom = Temporal_Coding()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
