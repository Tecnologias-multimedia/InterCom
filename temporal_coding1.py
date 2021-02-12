#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (temporal_coding1.py). '''

import numpy as np
import sounddevice as sd
import pywt
import time
import minimal
import compress
from compress import Compression as Compression
import br_control
from br_control import BR_Control as BR_Control 
import stereo_coding
from stereo_coding import Stereo_Coding as Stereo_Coding
from stereo_coding import Stereo_Coding__verbose as Stereo_Coding__verbose

minimal.parser.add_argument("-w", "--wavelet_name", type=str, default="db5", help="Name of the wavelet")
minimal.parser.add_argument("-e", "--levels", type=str, help="Number of levels of DWT")

class Temporal_Coding(Stereo_Coding):
    '''Removes first intra-channel redudancy and then, intra-frame redudancy.

    '''
    def __init__(self):
        super().__init__()
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
        DWT_chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int16)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            #assert np.all( channel_DWT_chunk < (1<<31) )
            assert np.all( abs(channel_DWT_chunk) < (1<<15) )
            DWT_chunk[:, c] = np.rint(channel_DWT_chunk).astype(np.int16)
        return DWT_chunk

    def pack(self, chunk_number, chunk):
        #chunk = Stereo_Coding.analyze(self, chunk)
        chunk = self.analyze(chunk)
        quantized_chunk = BR_Control.quantize(self, chunk)
        compressed_chunk = Compression.pack(self, chunk_number, quantized_chunk)
        return compressed_chunk

    def synthesize(self, chunk_DWT):
        '''Inverse DWT.'''
        chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int16)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(np.int16)
        return chunk

    def unpack(self, compressed_chunk):
        chunk_number, quantized_chunk = Compression.unpack(self, compressed_chunk)
        chunk = BR_Control.dequantize(self, quantized_chunk)
        chunk = self.synthesize(chunk)
        #chunk = Stereo_Coding.synthesize(self, chunk)
        return chunk_number, chunk

class Temporal_Coding__verbose(Temporal_Coding, Stereo_Coding__verbose):
    ''' Verbose version of Decorrelation. '''
    pass

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Temporal_Coding__verbose()
    else:
        intercom = Temporal_Coding()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
