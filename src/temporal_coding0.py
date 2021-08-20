#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Removes first intra-channel redudancy and then, intra-frame redudancy.'''

import numpy as np
import pywt
import minimal
#from compress2 import Compression2 as Compression
#import br_control
#from br_control2 import BR_Control2 as BR_Control 
#from stereo_coding_32 import Stereo_Coding_32 as Stereo_Coding
from temporal_coding import Temporal_Coding
import logging

class Temporal_Coding0(Temporal_Coding):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def analyze(self, chunk):
        #print("DWT analyze")
        '''Forward DWT.'''
        DWT_chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            #assert np.all( channel_DWT_chunk < (1<<31) )
            #assert np.all( abs(channel_DWT_chunk) < (1<<24) )
            #DWT_chunk[:, c] = np.rint(channel_DWT_chunk).astype(np.int32)
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk

    def synthesize(self, chunk_DWT):
        '''Inverse DWT.'''
        chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            #chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(np.int32)
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        return chunk

    def pack_(self, chunk_number, chunk):
        #return Stereo_Coding.pack(self, chunk_number, chunk)
        return super().pack(chunk_number, chunk)

    def unpack_(self, compressed_chunk):
        #return Stereo_Coding.unpack(self, compressed_chunk)
        return super().unpack(compressed_chunk)

from temporal_coding import Temporal_Coding__verbose

class Temporal_Coding0__verbose(Temporal_Coding0, Temporal_Coding__verbose):
    ''' Verbose version of Decorrelation. '''
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
        intercom = Temporal_Coding0__verbose()
    else:
        intercom = Temporal_Coding0()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
