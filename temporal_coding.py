#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (temporal_coding.py). '''

import numpy as np
import pywt
import minimal
#import buffer
#from compress2 import Compression2 as Compression
#from br_control2 import BR_Control2 as BR_Control
from stereo_coding1 import Stereo_Coding1 as Stereo_Coding

minimal.parser.add_argument("-w", "--wavelet_name", type=str, default="db5", help="Name of the wavelet")
minimal.parser.add_argument("-e", "--levels", type=str, help="Number of levels of DWT")

#class Temporal_Coding(buffer.Buffering):
class Temporal_Coding(Stereo_Coding):
#class Temporal_Coding(BR_Control):
    '''Removes the intra-channel redundancy between the samples of the
    same channel of each chunk using the DWT.

    '''
    def __init__(self):
        if __debug__:
            print("Running Temporal_Coding.__init__")
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

    def analyze_(self, chunk):
        print("DWT analyze")
        '''Forward DWT.'''
        DWT_chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int16)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            #assert np.all( channel_DWT_chunk < (1<<31) )
            #assert np.all( abs(channel_DWT_chunk) < (1<<15) )
            DWT_chunk[:, c] = np.rint(channel_DWT_chunk).astype(np.int16)
        return DWT_chunk

    def synthesize_(self, chunk_DWT):
        '''Inverse DWT.'''
        chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int16)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(np.int16)
        return chunk

    def pack_(self, chunk_number, chunk):
        #return Stereo_Coding.pack(self, chunk_number, chunk)
        return super().pack(chunk_number, chunk)

    def unpack_(self, compressed_chunk):
        #return Stereo_Coding.unpack(self, compressed_chunk)
        return super().unpack(compressed_chunk)

from stereo_coding1 import Stereo_Coding1__verbose as Stereo_Coding__verbose
from br_control2 import BR_Control2__verbose as BR_Control__verbose

class Temporal_Coding__verbose(Temporal_Coding, Stereo_Coding__verbose):
#class Temporal_Coding__verbose(Temporal_Coding, BR_Control__verbose):

    def __init__(self):
        if __debug__:
            print("Running Temporal_Coding__verbose.__init__")
        super().__init__()

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
