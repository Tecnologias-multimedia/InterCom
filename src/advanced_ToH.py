#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Considering the threshold of human hearing using the Hamming Window and the Fourier Transform. '''

import numpy as np
import math
import minimal
import logging

from basic_ToH import Treshold
from basic_ToH import Treshold__verbose
from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT


class AdvancedTreshhold(Treshold):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def analyze_hamming_fft(self, chunk, size):
        hamming_window = np.hamming(size)
        chunk[:, 0] = (chunk[:, 0] / hamming_window).astype(np.int32)
        chunk[:, 1] = (chunk[:, 1] / hamming_window).astype(np.int32)
        return np.fft.fft(chunk)

    def analyze(self, chunk):
        chunk_DWT = Temporal_Overlapped_DWT.analyze(self, chunk)

        # Quantize the subbands
        chunk_DWT[self.slices[0][0]] = (self.analyze_hamming_fft(
            chunk_DWT[self.slices[0][0]], chunk_DWT[self.slices[0][0]].shape[0]) / self.quantization_steps[0]).astype(np.int32)
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = (
                self.analyze_hamming_fft(
                    chunk_DWT[self.slices[i+1]['d'][0]], chunk_DWT[self.slices[i+1]['d'][0]].shape[0]) / self.quantization_steps[i+1]).astype(np.int32)

        return chunk_DWT

    def synthesize_hamming_fft(self, chunk, size):
        hamming_window = np.hamming(size)
        chunk = np.fft.ifft(chunk)
        chunk[:, 0] = (chunk[:, 0] * hamming_window).astype(np.int32)
        chunk[:, 1] = (chunk[:, 1] * hamming_window).astype(np.int32)
        return chunk

    def synthesize(self, chunk_DWT):

        # Dequantize the subbands
        chunk_DWT[self.slices[0][0]] = self.synthesize_hamming_fft(
            chunk_DWT[self.slices[0][0]], chunk_DWT[self.slices[0][0]].shape[0]) * self.quantization_steps[0]
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = self.synthesize_hamming_fft(
                chunk_DWT[self.slices[i+1]['d'][0]], chunk_DWT[self.slices[i+1]['d'][0]].shape[0]) * self.quantization_steps[i+1]

        return Temporal_Overlapped_DWT.synthesize(self, chunk_DWT)


class AdvancedTreshold__verbose(AdvancedTreshhold, Treshold__verbose):
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
        intercom = AdvancedTreshold__verbose()
    else:
        intercom = AdvancedTreshhold()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
