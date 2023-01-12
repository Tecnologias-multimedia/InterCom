#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Considering the threshold of human hearing. '''


import numpy as np
import math
import minimal
import logging
from scipy.fftpack import fft

from basic_ToH import Threshold
from basic_ToH import Threshold__verbose

minimal.parser.add_argument('--divisions', type=int, default=1,
                            help='Number of divisions for each subband')

class AdvancedThreshold(Threshold):

    def apply_fft(self, subband):
        if len(subband) == 0:
            # Handle the case where the input subband is empty
            raise ValueError("Cannot apply FFT to empty subband")
        else:
            return fft(subband)


    def divide_subbands(self, chunk_DWT, divisions):
        if len(chunk_DWT) == 0:
            # Handle the case where the input chunk of DWT data is empty
            raise ValueError("Cannot divide empty chunk of DWT data")
        divided_chunk_DWT = chunk_DWT.copy()  # copy data chunk
        for i in range(self.dwt_levels):
            # you get the sub-bands of the i-th level
            subbands = divided_chunk_DWT[self.slices[i+1]['d'][0]]
            # divide each sub-band into as many sub-bands as there are divisions required
            divided_subbands = np.array_split(subbands, divisions, axis=1)
            # apply FFT to each subband
            divided_subbands = [self.apply_fft(subband) for subband in divided_subbands]
            # reconstruct the data chunk with the divided and transformed sub-bands
            divided_chunk_DWT[self.slices[i+1]['d'][0]] = np.concatenate(divided_subbands, axis=1)
        return divided_chunk_DWT


    
    def analyze(self, chunk):
        chunk_DWT = super().analyze(chunk)  # run the DWT of the data chunk
        divisions = minimal.args.divisions  # read the number of divisions required by the 'divisions' argument
        chunk_DWT = self.divide_subbands(chunk_DWT, divisions)  # perform sub-band division
        # Quantize sub-bands as in the original class
        chunk_DWT[self.slices[0][0]] = (chunk_DWT[self.slices[0][0]] / self.quantization_steps[0]).astype(np.int32)
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = (chunk_DWT[self.slices[i+1]['d'][0]] / self.quantization_steps[i+1]).astype(np.int32)
        return chunk_DWT

    def synthesize(self, chunk_DWT):
        divisions = minimal.args.divisions  # read the number of divisions required by the 'divisions' argument
        chunk_DWT = self.divide_subbands(chunk_DWT, divisions)  # perform sub-band division

        # Dequantitise sub-bands as in the original class
        chunk_DWT[self.slices[0][0]] = chunk_DWT[self.slices[0][0]] * self.quantization_steps[0]
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = chunk_DWT[self.slices[i+1]['d'][0]] * self.quantization_steps[i+1]

        # Perform inverse DWT (IDWT) to reconstruct the original signal
        return super().synthesize(chunk_DWT)




  


class AdvancedThreshold__verbose(AdvancedThreshold, Threshold__verbose):
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
        intercom = AdvancedThreshold__verbose()
    else:
        intercom = AdvancedThreshold()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()