
''' Considering the threshold of human hearing using FFT. '''

import numpy as np
import minimal
import logging

from basic_ToH import Treshold
from basic_ToH import Treshold__verbose
from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT

class Treshold_Advanced(Treshold):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

        # Division number of each subband
        self.subbands_division_number = 2
        

    def subbands_divisor_fft(self, chunk_DWT):

        for i in range(self.dwt_levels):

            original_subbands = chunk_DWT[self.slices[i+1]['d'][0]]

            # Window size = 1 because, our implementation does not work
            size = 1
            window = np.blackman(size) 

            # Windowed subbands following blackman 
            windowed_subbands = np.multiply(original_subbands, window)

            # Divide subbands in "subbands_division_number" parameter
            divided_subbands = np.array_split(windowed_subbands, self.subbands_division_number, axis=0)

            # Apply FFT to each subband 
            fft_subbands = [np.fft.fft(subband) for subband in divided_subbands]

            # Rebuild the chunk from the processing of subbands
            chunk_DWT[self.slices[i+1]['d'][0]] = np.concatenate(fft_subbands, axis=0)

        return chunk_DWT


    def analyze(self, chunk):
        # Inheritance of Temporal_Overlapped_DWT
        chunk_DWT = Temporal_Overlapped_DWT.analyze(self, chunk)

        # Subbands division according to "subbands_division_number" parameter and after apply FFT
        chunk_DWT = self.subbands_divisor_fft(chunk_DWT)

        # Quantize the subbands
        chunk_DWT[self.slices[0][0]] = (chunk_DWT[self.slices[0][0]] / self.quantization_steps[0]).astype(np.int32)
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = (chunk_DWT[self.slices[i+1]['d'][0]] / self.quantization_steps[i+1]).astype(np.int32)
        return chunk_DWT

    def subbands_divisor_ifft(self, chunk_DWT):

        for i in range(self.dwt_levels):

            original_subbands = chunk_DWT[self.slices[i+1]['d'][0]]

            # Divide subbands in "subbands_division_number" parameter
            divided_subbands = np.array_split(original_subbands, self.subbands_division_number, axis=0)

            # Apply IFFT to each subband 
            ifft_subbands = [np.fft.ifft(subband) for subband in divided_subbands]

            # Window size = 1 because, our implementation does not work
            size = 1
            window = np.blackman(size) 

            # Windowed subbands following blackman 
            windowed_subbands = np.multiply(ifft_subbands, window)

            # Rebuild the chunk from the processing of subbands
            chunk_DWT[self.slices[i+1]['d'][0]] = np.concatenate(windowed_subbands, axis=0)

        return chunk_DWT

    def synthesize(self, chunk_DWT):
        # Subbands division according to "subbands_division_number" parameter and after apply IFFT
        chunk_DWT = self.subbands_divisor_ifft(chunk_DWT)

        # Dequantize the subbands
        chunk_DWT[self.slices[0][0]] = chunk_DWT[self.slices[0][0]] * self.quantization_steps[0]
        for i in range(self.dwt_levels):
            chunk_DWT[self.slices[i+1]['d'][0]] = chunk_DWT[self.slices[i+1]['d'][0]] * self.quantization_steps[i+1]

        # Inheritance of Temporal_Overlapped_DWT
        return Temporal_Overlapped_DWT.synthesize(self, chunk_DWT)


class Treshold_Advanced__verbose(Treshold_Advanced, Treshold__verbose):
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
        intercom = Treshold_Advanced__verbose()
    else:
        intercom = Treshold_Advanced()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
