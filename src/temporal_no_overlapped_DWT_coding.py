#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Removes the temporal (intra-channel) redundancy using the DWT. First the spatial (inter-channel) redundancy is removed.'''

# Rename to temporal_coding0.py

import numpy as np
import pywt  # pip install pywavelets
import logging

import minimal
from stereo_MST_coding_16 import Stereo_MST_Coding_16 as Stereo_Coding
#from stereo_MST_coding_32 import Stereo_MST_Coding_32 as Stereo_Coding

minimal.parser.add_argument("-w", "--wavelet_name", type=str, default="db5", help="Name of the wavelet")
minimal.parser.add_argument("-e", "--levels", type=str, default="3", help="Number of levels of DWT")

class Temporal_No_Overlapped_DWT(Stereo_Coding):

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
        chunk = super().analyze(chunk)
        DWT_chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            #assert np.all( channel_DWT_chunk < (1<<31) )
            #assert np.all( abs(channel_DWT_chunk) < (1<<24) )
            #DWT_chunk[:, c] = np.rint(channel_DWT_chunk).astype(np.int32)
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk

    def synthesize(self, chunk_DWT):
        '''Inverse DWT.'''
        chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            #chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(np.int32)
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        chunk = super().synthesize(chunk)
        return chunk
'''
    def pack_(self, chunk_number, chunk):
        #return Stereo_Coding.pack(self, chunk_number, chunk)
        return super().pack(chunk_number, chunk)

    def unpack_(self, compressed_chunk):
        #return Stereo_Coding.unpack(self, compressed_chunk)
        return super().unpack(compressed_chunk)
'''
from stereo_MST_coding_32 import Stereo_MST_Coding_32__verbose as Stereo_Coding__verbose

class Temporal_No_Overlapped_DWT__verbose(Temporal_No_Overlapped_DWT, Stereo_Coding__verbose):
    pass
    #def ___init__(self):
    #    super().__init__()
'''
    def _analyze(self, chunk):
        analyzed_chunk = Temporal_Coding0.analyze(self, chunk)
        self.LH_chunks_in_the_cycle.append(analyzed_chunk)
        return analyzed_chunk

    def __analyze(self, chunk):
        return Temporal_Coding__verbose.analyze(self, chunk)
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
        intercom = Temporal_No_Overlapped_DWT__verbose()
    else:
        intercom = Temporal_No_Overlapped_DWT()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
