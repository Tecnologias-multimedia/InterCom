#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Considering the threshold of human hearing using the Hamming Window and the Fourier Transform. '''

import numpy as np
import minimal
import logging

from basic_ToH import Treshold
from basic_ToH import Treshold__verbose
from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT

minimal.parser.add_argument('--split', type=int, default=1,
                            help='Number of times the wavelets subband will be split')


class AdvancedTreshhold(Treshold):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def analyze_hamming_fft(self, chunk):
        # Split the chunk into multiple parts
        split = minimal.args.split
        split_chunks = np.array_split(chunk, split, axis=0)

        # Apply the hamming window to each part of the chunk
        for i in range(len(split_chunks)):
            hamming_window = np.hamming(len(split_chunks[i]))
            split_chunks[i][:, 0] = (
                split_chunks[i][:, 0] / hamming_window).astype(np.int32)
            split_chunks[i][:, 1] = (
                split_chunks[i][:, 1] / hamming_window).astype(np.int32)

        # Apply the FFT to each part of the chunk
        fft_chunks = [np.fft.fft(split_chunk)
                      for split_chunk in split_chunks]

        return np.concatenate(fft_chunks, axis=0)

    def analyze(self, chunk):
        chunk_DWT = Temporal_Overlapped_DWT.analyze(self, chunk)

        # Quantize the subbands
        chunk_DWT[self.slices[0][0]] = (self.analyze_hamming_fft(
            chunk_DWT[self.slices[0][0]]) / self.quantization_steps[0]).astype(np.int32)
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = (
                self.analyze_hamming_fft(
                    chunk_DWT[self.slices[i+1]['d'][0]]) / self.quantization_steps[i+1]).astype(np.int32)

        return chunk_DWT

    def synthesize_hamming_fft(self, chunk):
        # Split the chunk into multiple parts and apply the IFFT to each part
        split = minimal.args.split
        split_chunks = np.array_split(chunk, split, axis=0)
        fft_chunks = [np.fft.ifft(split_chunk) for split_chunk in split_chunks]

        # Apply the inverse of the Hamming window to each part of the chunk
        for i in range(len(fft_chunks)):
            hamming_window = np.hamming(len(fft_chunks[i]))
            fft_chunks[i][:, 0] = (
                fft_chunks[i][:, 0] * hamming_window).astype(np.int32)
            fft_chunks[i][:, 1] = (
                fft_chunks[i][:, 1] * hamming_window).astype(np.int32)

        return np.concatenate(fft_chunks, axis=0)

    def synthesize(self, chunk_DWT):

        # Dequantize the subbands
        chunk_DWT[self.slices[0][0]] = self.synthesize_hamming_fft(
            chunk_DWT[self.slices[0][0]]) * self.quantization_steps[0]
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = self.synthesize_hamming_fft(
                chunk_DWT[self.slices[i+1]['d'][0]]) * self.quantization_steps[i+1]

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
