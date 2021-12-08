#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import numpy as np
import pywt
import logging
import time

import minimal
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT as temp_no_DWT

class Temporal_Overlapped_DWT(temp_no_DWT):
    #WIP
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

    def encoder(self,chunk):
        chunk= super().analyze(chunk)
        previous_chunk = np.zeros(shape= minimal.args.frames_per_chunk)
        time.sleep(self.chunk_time)
        next_chunk= super().analyze(chunk);    
        
        for i in range (self.NUMBER_OF_CHANNELS):
            e = np.concatenate(previous_chunk[-self.slices:], chunk,next_chunk[:self.slices])
            d= super().analyze(e)            
            previous_chunk= chunk;
            chunk = next_chunk;
            
        return d;


from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT__verbose as temp_no_DWT_verbose

class Temporal_Overlapped_DWT__verbose(Temporal_Overlapped_DWT,temp_no_DWT_verbose):
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
        intercom = Temporal_Overlapped_DWT__verbose()
    else:
        intercom = Temporal_Overlapped_DWT()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()


