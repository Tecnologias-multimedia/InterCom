#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Considering the threshold of human hearing. '''

import numpy as np
import math
import minimal
import logging

from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT
from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT__verbose

class Treshold(Temporal_Overlapped_DWT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

        # Calculate quantization step for each subband
        # Modify max_q to change the amount of quantization
        self.quantization_steps = self.calculate_quantization_steps(max_q=64)

    def calculate_quantization_steps(self, max_q):

        # Threshold of human hearing formula
        def calc(f):
            return 3.64*(f/1000)**(-0.8) - 6.5*math.exp((-0.6)*(f/1000-3.3)**2) + 10**(-3)*(f/1000)**4

        f=22050
        average_SPLs = []

        # Calculate average SPL[dB] for each frequency subband
        for i in range(self.dwt_levels):
            mean = 0
            for j in np.arange(f/2,f,1):
                mean += calc(j)
            f = f/2
            average_SPLs.insert(0,mean/f)
        mean = 0
        for j in np.arange(1,f,1):
            mean += calc(j)
        average_SPLs.insert(0,mean/f)

        # Map the SPL values to quantization steps, from 1 to max_q
        # https://stackoverflow.com/questions/345187/math-mapping-numbers
        quantization_steps = []
        min_SPL = np.min(average_SPLs)
        max_SPL = np.max(average_SPLs)
        for i in range(len(average_SPLs)):
            quantization_steps.append( round((average_SPLs[i]-min_SPL)/(max_SPL-min_SPL)*(max_q-1)+1) )

        return quantization_steps


    def analyze(self, chunk):
        chunk_DWT = super().analyze(chunk)

        # Quantize the subbands
        chunk_DWT[self.slices[0][0]] = (chunk_DWT[self.slices[0][0]] / self.quantization_steps[0]).astype(np.int32)
        for i in range (self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = (chunk_DWT[self.slices[i+1]['d'][0]] / self.quantization_steps[i+1]).astype(np.int32)

        return chunk_DWT


    def synthesize(self, chunk_DWT):

        # Dequantize the subbands
        chunk_DWT[self.slices[0][0]] = chunk_DWT[self.slices[0][0]] * self.quantization_steps[0]
        for i in range (self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = chunk_DWT[self.slices[i+1]['d'][0]] * self.quantization_steps[i+1]

        return super().synthesize(chunk_DWT)
        

class Treshold__verbose(Treshold, Temporal_Overlapped_DWT__verbose):
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
        intercom = Treshold__verbose()
    else:
        intercom = Treshold()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
