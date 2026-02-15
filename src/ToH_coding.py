#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Adapting the QSSs to the Threshold of Hearing. '''

import numpy as np
import logging
import math
import minimal
from temporal_overlapped_WPT_coding import Temporal_Overlapped_WPT

class ToH(Temporal_Overlapped_WPT):

    PERSONAL_SCALE = 128
    
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

        avg_SPLs = self.get_average_SPLs()
        min_avg_SPLs = np.min(avg_SPLs)
        positive_avg_SPLs = avg_SPLs + np.abs(min_avg_SPLs)
        print("positive_avg_SPLs", positive_avg_SPLs)
        self.QSSs = positive_avg_SPLs + minimal.args.minimal_quantization_step_size
        self.QSSs[self.QSSs < 1] = 1
        self.quantization_step_size = np.min(self.QSSs) + 1
        logging.info(f"Average Sound Preasure Levels in the ToH = {self.QSSs}")
        self.coef_QSSs = np.empty_like(self.zero_chunk)
        #self.QSSs[:, 0] = np.repeat(self.average_SPLs, self.subbands_length)
        #self.QSSs[:, 1] = self.QSSs[:, 0]

    def ToH_model(self, f):
        '''
        f is in Hz.
        '''
        #return 1
        # set xrange[0:22050]; plot 16.97 * (log10(x) ** 2) - 106.98 * log10(x) + 173.82 + 10 ** -3 * (x / 1000) ** 4, 3.64 * (x / 1000) ** -0.8 - 6.5 * exp((-0.6) * (x / 1000 - 3.3) ** 2) + 10 ** -3 * (x / 1000) ** 4
        #return 16.97 * (np.log10(f) ** 2) - 106.98 * np.log10(f) + 173.82 + 10 ** -3 * (f / 1000) ** 4
        # set xrange[0:22050]; lot 3.64*(x/1000)**(-0.8) - exp((-0.6)*(x/1000-3.3)**2) + 10**(-3)*(x/1000)**4
        return 3.64*(f/1000)**(-0.8) - 6.5*math.exp((-0.6)*(f/1000-3.3)**2) + 10**(-3)*(f/1000)**4

    def linear_ToH_model(self, f):
        return 10**(self.ToH_model(f)/10)

    def get_average_SPLs(self):
        '''
        Calculate the averge Sound Preasure Level of the ToH for each WPT subband.
        '''
        self.Nyquist_frequency = minimal.args.frames_per_second // 2
        self.subbands_bandwidth = self.Nyquist_frequency / self.number_of_subbands
        # Average Sound Preassure Levels of the threshold of hearing
        average_SPLs = []  
        for i in range(self.number_of_subbands):
            start_freq = i*self.subbands_bandwidth
            end_freq = (i + 1)*self.subbands_bandwidth
            #print(start_freq, end_freq)
            steps = np.linspace(start_freq, end_freq, 10) + 1
            SPLs = [self.ToH_model(f) for f in steps]
            #SPLs = [np.sqrt(12*self.linear_ToH_model(f)) for f in steps]
            print("SPLs", SPLs)
            avg_SPL = np.mean(SPLs)
            #print(avg_SPL)
            average_SPLs.append(avg_SPL)
        average_SPLs = np.array(average_SPLs)
        
        return average_SPLs

    def normalize_SPLs(self):

        def normalize(x):
            min_x = np.min(x)
            max_x = np.max(x)
            maxmin_x = max_x - min_x
            if maxmin_x != 0:
                #print(max_x, min_x)
                return (x - min_x)/maxmin_x
            else:
                return np.ones_like(x)
            
        min_val = np.min(SPLs)
        max_val = np.max(SPLs)
        normalized_values = (SPLs - min_val) / (max_val - min_val)
        #for i in normalized_values:
        #    print(i, end=' ')

        QSSs = []
        for freq, val in zip(frequencies, normalized_values):
            q = int(val*self.quantization_step_size)
            QSSs.append(q)
        QSSs = np.array(QSSs)
        QSSs_per_coef = np.repeat(QSSs, self.subbands_length)
        stereo_QSSs_per_coef = np.empty_like(self.zero_chunk)
        stereo_QSSs_per_coef[:, 0] = QSSs_per_coef
        stereo_QSSs_per_coef[:, 1] = QSSs_per_coef
        return stereo_QSSs_per_coef
        '''
        Nyquist_frequency = minimal.args.frames_per_second // 2
        self.subbands_bandwidth = Nyquist_frequency / self.number_of_subbands
        SPLs = []  # Sound Preassure Levels of the threshold of hearing
        for i in range(int(Nyquist_frequency)):
            SPLs.append(linear_ToH_model(i+1))
        SPLs = np.array(SPLs)
        print("1.", SPLs)

        average_SPLs = []
        for i in range(1, self.number_of_subbands+1):
            start_freq = i * self.subbands_bandwidth
            end_freq = (i+1) * self.subbands_bandwidth
            samples_in_the_subband = np.linspace(start_freq, end_freq, 1)
            average = np.mean([ToH_model(val+1) for val in samples_in_the_subband])
            average_SPLs.append(average)
        average_SPLs = np.array(average_SPLs).astype(np.int32)
        average_SPLs -= np.min(average_SPLs)
        #average_SPLs += 1
        print("2.", average_SPLs)
        #print_SPLs(average_SPLs)
        min_SPL = np.min(average_SPLs)
        max_SPL = np.max(average_SPLs)
        normalized_SPLs = (average_SPLs - min_SPL) / (max_SPL - min_SPL)
        print("3.", 12*normalized_SPLs)
        nose = (1+np.sqrt(12*normalized_SPLs)) * self.quantization_step_size
        nose = average_SPLs + self.quantization_step_size
        print_SPLs(nose)
        shifted_SPLs = normalized_SPLs + 1

        QSSs = []
        for s in nose:
            #q = int(self.quantization_step_size + (s - min_SPL) / (max_SPL - min_SPL))
            #q = int(self.quantization_step_size + s)
            #if s < 1: s = 1
            #q = math.sqrt(12*s) * self.quantization_step_size
            q = s #+ self.quantization_step_size
            #if q < 1: q = 1
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
        '''
    
    def quantize(self, chunk):
        '''Deadzone quantizer using different QSS per subband.'''
        self.coef_QSSs[:, 0] = np.repeat(self.QSSs, self.subbands_length) + self.quantization_step_size
        self.coef_QSSs[:, 1] = self.coef_QSSs[:, 0]
        quantized_chunk = (chunk / self.coef_QSSs).astype(np.int32)
        #print("->", chunk, quantized_chunk, self.QSSs)
        return quantized_chunk

    def dequantize(self, quantized_chunk):
        chunk = quantized_chunk * self.coef_QSSs
        return chunk

from temporal_overlapped_WPT_coding import Temporal_Overlapped_WPT__verbose

class ToH__verbose(ToH, Temporal_Overlapped_WPT__verbose):

    def __init__(self):
        super().__init__()
        #self.print_average_SPLs()

    def print_average_SPLs(x):
        frequencies = np.linspace(0, self.Nyquist_frequency, self.number_of_subbands)
        min_val = np.min(x)
        max_val = np.max(x)
        if max_val != min_val:
            normalized_values = (x - min_val) / (max_val - min_val)
        else:
            normalized_values = np.ones_like(x)

        i = 1
        for freq, val in zip(frequencies, normalized_values):
            num_stars = int(val*80)
            print(f"{i:3} | {freq:5.0f} | {num_stars+1:2} | {'*' * (num_stars+1)}")
            i += 1

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
