#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Removes the intra-channel redundancy between the samples of the same channel of each chunk using a non-overlapped DWT.'''

import numpy as np
import pywt  # pip install pywavelets
import minimal
#import buffer
#from compress2 import Compression2 as Compression
#from br_control2 import BR_Control2 as BR_Control
from stereo_MST_coding_32 import Stereo_MST_Coding_32 as Stereo_Coding
import logging

minimal.parser.add_argument("-w", "--wavelet_name", type=str, default="db5", help="Name of the wavelet")
minimal.parser.add_argument("-e", "--levels", type=str, help="Number of levels of DWT")

#class Temporal_Coding(buffer.Buffering):
class Temporal_Coding(Stereo_Coding):
#class Temporal_Coding(BR_Control):
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
        return chunk

    def synthesize(self, DWT_chunk):
        return DWT_chunk

    def pack(self, chunk_number, chunk):
        #chunk = Stereo_Coding.analyze(self, chunk)
        analyzed_chunk = self.analyze(chunk)
        #chunk = super().analyze(chunk)
        #quantized_chunk = self.quantize(chunk)
        #quantized_chunk = br_control.BR_Control.quantize(self, chunk)
        #chunk = chunk.astype(np.int16)
        #print(quantized_chunk.shape, np.dtype(quantized_chunk))
        #compressed_chunk = Compression.pack(self, chunk_number, quantized_chunk)
        packed_chunk = super().pack(chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = super().unpack(packed_chunk)
        chunk = self.synthesize(analyzed_chunk)
        return chunk_number, chunk
    
    def unpack_(self, compressed_chunk):
        chunk_number, quantized_chunk = Compression.unpack(self, compressed_chunk)
        print(quantized_chunk.shape)
        chunk = self.dequantize(quantized_chunk)
        #chunk = br_control.BR_Control.dequantize(self, quantized_chunk)
        chunk = super().synthesize(chunk)
        #chunk = Stereo_Coding.synthesize(self, chunk)
        return chunk_number, chunk

from stereo_MST_coding_32 import Stereo_MST_Coding_32__verbose as Stereo_Coding__verbose
#from br_control2 import BR_Control2__verbose as BR_Control__verbose

class Temporal_Coding__verbose(Temporal_Coding, Stereo_Coding__verbose):
#class Temporal_Coding__verbose(Temporal_Coding, BR_Control__verbose):

    def __init__(self):
        super().__init__()

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
