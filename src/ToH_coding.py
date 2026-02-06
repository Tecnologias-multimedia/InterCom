#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Adapting the QSSs to the Threshold of Hearing. '''

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
        for i in self.QSSs:
            print(i, end=' ')

    def get_QSSs(self):
        '''
        Calculate The Quantization Step Size (QSS) for each WPT subband.
        '''

        def ToH_model(f):
            #return 1
            # plot 16.97 * (log10(x) ** 2) - 106.98 * log10(x) + 173.82 + 10 ** -3 * (x / 1000) ** 4, 3.64 * (x / 1000) ** -0.8 - 6.5 * exp((-0.6) * (x / 1000 - 3.3) ** 2) + 10 ** -3 * (x / 1000) ** 4
            #return 16.97 * (np.log10(f) ** 2) - 106.98 * np.log10(f) + 173.82 + 10 ** -3 * (f / 1000) ** 4
            return 3.64*(f/1000)**(-0.8) - 6.5*math.exp((-0.6)*(f/1000-3.3)**2) + 10**(-3)*(f/1000)**4

        def print_SPLs(SPLs):
            frequencies = np.linspace(0, 22050, self.number_of_subbands)
            min_val = np.min(SPLs)
            max_val = np.max(SPLs)
            normalized_values = (SPLs - min_val) / (max_val - min_val)

            i = 1
            for freq, val in zip(frequencies, normalized_values):
                num_stars = int(val*80)
                print(f"{i:3} | {freq:5.0f} | {num_stars+1:2} | {'*' * (num_stars+1)}")
                i += 1

        Nyquist_frequency = minimal.args.frames_per_second // 2
        self.subbands_bandwidth = Nyquist_frequency / self.number_of_subbands
        SPLs = []
        for i in range(int(Nyquist_frequency)):
            SPLs.append(ToH_model(i+1))
        SPLs = np.array(SPLs)

        average_SPLs = []
        for i in range(1, self.number_of_subbands+1):
            start_freq = i * self.subbands_bandwidth
            end_freq = (i+1) * self.subbands_bandwidth
            steps = np.linspace(start_freq, end_freq, 1)
            average = np.mean([ToH_model(val+1) for val in steps])
            average_SPLs.append(average)
        average_SPLs = np.array(average_SPLs).astype(np.int32)
        print(average_SPLs)
        #print_SPLs(average_SPLs)
        min_SPL = np.min(average_SPLs)
        max_SPL = np.max(average_SPLs)

        QSSs = []
        for s in average_SPLs:
            #q = int(self.quantization_step_size + (s - min_SPL) / (max_SPL - min_SPL))
            q = int(self.quantization_step_size + s)
            if q < 1: q = 1
            QSSs.append(q)
        QSSs = np.array(QSSs)
        #for i in QSSs:
        #    print(i, end=' ')
        #quit()
        QSSs_per_coef = np.repeat(QSSs, self.subbands_length)
        stereo_QSSs_per_coef = np.empty_like(self.zero_chunk)
        stereo_QSSs_per_coef[:, 0] = QSSs_per_coef
        stereo_QSSs_per_coef[:, 1] = QSSs_per_coef
        return stereo_QSSs_per_coef
    
    def quantize(self, chunk):
        '''Deadzone quantizer using different QSS per subband.'''
        quantized_chunk = (chunk / self.QSSs).astype(np.int32)
        #print("->", chunk, quantized_chunk, self.QSSs)
        return quantized_chunk

    def dequantize(self, quantized_chunk):
        chunk = quantized_chunk * self.QSSs
        return chunk

from temporal_overlapped_WPT_coding import Temporal_Overlapped_WPT__verbose

class ToH__verbose(ToH, Temporal_Overlapped_WPT__verbose):
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
