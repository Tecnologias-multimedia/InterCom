#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Removes first intra-frame redudancy and then, intra-channel redundancy.'''

import numpy as np
import sounddevice as sd
import pywt  # pip install pywavelets
import time
import minimal
import compress
import buffer
from compress3_24 import Compression3_24 as Compression
from br_control import BR_Control as BR_Control 
import stereo_coding
from stereo_MST_coding import Stereo_MST_Coding as Stereo_Coding
import temporal_coding
import logging

class Temporal_Coding1(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.wavelet = pywt.Wavelet(minimal.args.wavelet_name)
        
        # Default dwt_levels is based on the length of the chunk and the length of the filter
        max_filters_length = max(self.wavelet.dec_len, self.wavelet.rec_len)
        self.dwt_levels = pywt.dwt_max_level(data_len=minimal.args.frames_per_chunk//4, filter_len=max_filters_length)
        if minimal.args.levels:
            self.dwt_levels = int(minimal.args.levels)

        # Structure used during the decoding
        zero_array = np.zeros(shape=minimal.args.frames_per_chunk)
        coeffs = pywt.wavedec(zero_array, wavelet=self.wavelet, level=self.dwt_levels, mode="per")
        self.slices = pywt.coeffs_to_array(coeffs)[1]

        print("Performing intra-channel decorrelation")
        if __debug__:
            print("wavelet name =", minimal.args.wavelet_name)
            print("analysis filters's length =", self.wavelet.dec_len)
            print("synthesis filters's length =", self.wavelet.rec_len)
            print("DWT levels =", self.dwt_levels)

    def analyze(self, chunk):
        '''Forward DWT.'''
        DWT_chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            #assert np.all( channel_DWT_chunk < (1<<31) )
            #assert np.all( abs(channel_DWT_chunk) < (1<<15) )
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk

    def synthesize(self, chunk_DWT):
        '''Inverse DWT.'''
        chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        return chunk

    def pack(self, chunk_number, chunk):
        chunk = Stereo_Coding.analyze(self, chunk)
        chunk = self.analyze(chunk)
        quantized_chunk = BR_Control.quantize(self, chunk)
        compressed_chunk = Compression.pack(self, chunk_number, quantized_chunk)
        return compressed_chunk

    def unpack(self, compressed_chunk):
        chunk_number, quantized_chunk = Compression.unpack(self, compressed_chunk)
        chunk = BR_Control.dequantize(self, quantized_chunk)
        chunk = self.synthesize(chunk)
        chunk = Stereo_Coding.synthesize(self, chunk)
        return chunk_number, chunk

from temporal_coding import Temporal_Coding__verbose

class Temporal_Coding1__verbose(Temporal_Coding1, Temporal_Coding__verbose):
    pass

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
        intercom = Temporal_Coding1__verbose()
    else:
        intercom = Temporal_Coding1()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
