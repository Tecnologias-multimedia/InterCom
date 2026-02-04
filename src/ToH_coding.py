#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Adapting the QSSs to the Threshold of Hearing.
"""

import numpy as np
import logging
import minimal
from temporal_overlapped_WPT_coding import Temporal_Overlapped_WPT

class ToH(Temporal_Overlapped_WPT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.QSSs = self.get_QSSs(max_expected_q=1024)

    def get_QSSs(self, max_expected_q):
        """
        Calculate Quantization Step Sizes (QSS) for each subband based on Wavelet Packet decomposition.
        """

        def print_shape(start_freq=50, end_freq=22050, num_points=2**self.DWT_levels, max_width=100):
            """
            Prints a text-based representation of the shape described by the calc function,
            including a first column with the frequency.

            Args:
                start_freq (int): Starting frequency.
                end_freq (int): Ending frequency.
                num_points (int): Number of frequency points to evaluate.
                max_width (int): Maximum width of the printed shape.
            """

            frequencies = np.linspace(start_freq, end_freq, num_points)
            values = np.array([self.calc(f) for f in frequencies])

            # Normalize values to the range [0, 1]
            min_val = np.min(values)
            max_val = np.max(values)
            normalized_values = (values - min_val) / (max_val - min_val)

            i = 1
            for freq, val in zip(frequencies, normalized_values):
                num_stars = int(val * max_width)
                print(f"{i:3} | {freq:5.0f} | {num_stars+1:2} | {'*' * (num_stars+1)}")
                i += 1

        f = minimal.args.frames_per_second // 2
        print_shape(end_freq=f, num_points = self.number_of_subbands)
        frequencies = [(f / subbands) * (i + 0.5) for i in range(subbands)]
        SPL_values = np.array([self.calc(f) for f in frequencies])
        min_SPL = min(SPL_values)
        max_SPL = max(SPL_values)
        quantization_steps = np.array([
            round(((SPL - min_SPL) / (max_SPL - min_SPL) * (max_expected_q - 1) + 1) * minimal.args.minimal_quantization_step_size)
            for SPL in SPL_values
        ])
        logging.info(f"Quantization steps: {quantization_steps}")
        return quantization_steps

    def pack(self, chunk_number, chunk):
        for c in range(minimal.args.number_of_channels):
            chunk[:, c] /= self.QSSs
        packed_chunk = EC.pack(self, chunk_number, chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, chunk = EC.unpack(self, packed_chunk)
        for c in range(minimal.args.number_of_channels):
            chunk[:, c] *= self.QSSs
        return chunk_number, chunk

class ToH__verbose(ToH, Temporal_Overlapped_WPT):
    pass

try:
    import argcomplete
except ImportError:
    logging.warning("argcomplete not available.")

if __name__ == "__main__":
    minimal.parser.description = __doc__

    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working.")

    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = ToH__verbose()
    else:
        intercom = ToH()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received.")
    finally:
        intercom.print_final_averages()
