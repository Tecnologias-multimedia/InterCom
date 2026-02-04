#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Adapting the QSSs to the Threshold of Hearing.
"""

import numpy as np
import logging
import math
import minimal
from temporal_overlapped_WPT_coding import Temporal_Overlapped_WPT

class ToH(Temporal_Overlapped_WPT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        #self.QSSs = self.get_QSSs(max_expected_q=1024)
        self.QSSs = self.get_QSSs()

    def _get_QSSs(self, max_expected_q):
        """
        Calculate Quantization Step Sizes (QSS) for each subband based on Wavelet Packet decomposition.
        """

        def calc(f):
            #return 1
            # plot 16.97 * (log10(x) ** 2) - 106.98 * log10(x) + 173.82 + 10 ** -3 * (x / 1000) ** 4, 3.64 * (x / 1000) ** -0.8 - 6.5 * exp((-0.6) * (x / 1000 - 3.3) ** 2) + 10 ** -3 * (x / 1000) ** 4
            #return 16.97 * (np.log10(f) ** 2) - 106.98 * np.log10(f) + 173.82 + 10 ** -3 * (f / 1000) ** 4
            return 3.64*(f/1000)**(-0.8) - 6.5*math.exp((-0.6)*(f/1000-3.3)**2) + 10**(-3)*(f/1000)**4

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
            values = np.array([calc(f) for f in frequencies])

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
        frequencies = [(f / self.number_of_subbands) * (i + 0.5) for i in range(self.number_of_subbands)]
        SPL_values = np.array([calc(f) for f in frequencies])
        min_SPL = min(SPL_values)
        max_SPL = max(SPL_values)
        quantization_steps = np.array([
            round(((SPL - min_SPL) / (max_SPL - min_SPL) * (max_expected_q - 1) + 1) * minimal.args.minimal_quantization_step_size)
            for SPL in SPL_values
        ])
        logging.info(f"QSSs: {quantization_steps}")
        return np.array([quantization_steps, quantization_steps])

    def get_QSSs(self):
        '''
        Calculate The Quantization Step Size (QSS) for each WPT subband.
        '''

        def model_ToH(f):
            #return 1
            # plot 16.97 * (log10(x) ** 2) - 106.98 * log10(x) + 173.82 + 10 ** -3 * (x / 1000) ** 4, 3.64 * (x / 1000) ** -0.8 - 6.5 * exp((-0.6) * (x / 1000 - 3.3) ** 2) + 10 ** -3 * (x / 1000) ** 4
            #return 16.97 * (np.log10(f) ** 2) - 106.98 * np.log10(f) + 173.82 + 10 ** -3 * (f / 1000) ** 4
            return 3.64*(f/1000)**(-0.8) - 6.5*math.exp((-0.6)*(f/1000-3.3)**2) + 10**(-3)*(f/1000)**4

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
            values = np.array([model_ToH(f) for f in frequencies])

            # Normalize values to the range [0, 1]
            min_val = np.min(values)
            max_val = np.max(values)
            normalized_values = (values - min_val) / (max_val - min_val)

            i = 1
            for freq, val in zip(frequencies, normalized_values):
                num_stars = int(val * max_width)
                print(f"{i:3} | {freq:5.0f} | {num_stars+1:2} | {'*' * (num_stars+1)}")
                i += 1

        #print_shape(end_freq=f, num_points = self.number_of_subbands)
        number_of_Fourier_subbands = minimal.args.frames_per_second // 2
        frequencies = [(i+1) for i in range(number_of_Fourier_subbands)]
        ToH_SPLs = np.array([model_ToH(f) for f in frequencies])
        ToH_SPL_per_subband = np.array(ToH_SPLs)
        for i in range(0, len(ToH_SPLs), self.subbands_length):
            block = ToH_SPLs[i : i + self.subbands_length]
            ToH_SPL_per_subband[i : i + self.subbands_length] = np.mean(block)
        print(ToH_SPL_per_subband[::self.subbands_length])
        '''
        print("------>", ToH_values.astype(np.uint32))
        min_ToH = min(ToH_values)
        max_ToH = max(ToH_values)
        print(min_ToH, max_ToH, np.argmin(ToH_values), np.argmax(ToH_values))
        Fourier_QSSs = np.array([
            (1 + round(f - min_ToH))
            for f in ToH_values
        ])
        logging.info(f"Fourier QSSs: {Fourier_QSSs} min_val{np.min(Fourier_QSSs)} max_val={np.max(Fourier_QSSs)} min_index={np.argmin(Fourier_QSSs)} max_index={np.argmax(Fourier_QSSs)}")
        subband_QSSs = Fourier_QSSs.reshape(-1, self.subbands_length).mean(axis=1)

        #QSSs = np.rint(self.number_of_subbands * (1 + (QSSs - np.min(QSSs)) / (np.max(QSSs) - np.min(QSSs))))
        logging.info(f"QSSs: {subband_QSSs} {np.min(subband_QSSs)} {np.max(subband_QSSs)} {np.argmin(subband_QSSs)} {np.argmax(subband_QSSs)}")
        QSSs = np.repeat(subband_QSSs, self.subbands_length)
        '''
        QSSs = (ToH_SPL_per_subband * self.quantization_step_size).astype(np.int32)
        return np.array([QSSs, QSSs])
    
    def quantize(self, chunk):
        '''Deadzone quantizer using different QSS per subband.'''
        quantized_chunk = (chunk / self.QSSs).astype(np.int32)
        return quantized_chunk

    def dequantize(self, quantized_chunk):
        chunk = quantized_chunk * self.QSSs
        return chunk

    def __pack(self, chunk_number, chunk):
        for c in range(minimal.args.number_of_channels):
            chunk[:, c] = chunk[:, c] / self.QSSs
        packed_chunk = EC.pack(self, chunk_number, chunk)
        return packed_chunk

    def __unpack(self, packed_chunk):
        chunk_number, chunk = EC.unpack(self, packed_chunk)
        for c in range(minimal.args.number_of_channels):
            chunk[:, c] = chunk[:, c] * self.QSSs
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
