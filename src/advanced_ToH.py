#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import numpy as np
import scipy.fft as sp
import sounddevice as sd
import logging
import minimal

from basic_ToH import Treshold
from basic_ToH import Treshold__verbose

minimal.parser.add_argument("-nfftb", "--number_fft_bands", type=int, default=-1, help="Number of FFT bands for each wavelet band");

class Advance_Threshold(Treshold):
    def __init__(self):
        super().__init__();

    def calculate_quantization_steps(self,max_q,nFBands=-1):

        def obtain_qss(average_SPLs,max_q):
            # Map the SPL values to quantization steps, from 1 to max_q
            # https://stackoverflow.com/questions/345187/math-mapping-numbers
            quantization_steps = []
            min_SPL = np.min(average_SPLs)
            max_SPL = np.max(average_SPLs)
            for i in range(len(average_SPLs)):
                quantization_steps.append( round((average_SPLs[i]-min_SPL)/(max_SPL-min_SPL)*(max_q-1)+1) )

            return quantization_steps;

        # Centered and extreme frequencies methods only change amplitude and its increment.
        def obtain_db_centered_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq):
            imperceptible=True;
            amplitude=0.0001;
            while imperceptible:
                # White Noise
                nSamples = duration*fs;
                noise = amplitude*2*(np.random.rand(nSamples)-0.5);

                # Fourier Transform
                Noise = sp.fftshift(sp.fft(noise));

                # Filtering
                bpf = [1 if (abs(i)>=minFreqCut and abs(i)<=maxFreqCut) else 0 for i in np.linspace(-maxFreq, maxFreq, num=len(Noise))]; # BandPass filter
                FilteredWhiteNoise = np.multiply(Noise,bpf);

                # Inverse Transform
                FilteredWhiteNoise = sp.ifft(sp.ifftshift(FilteredWhiteNoise));
                FilteredWhiteNoise = np.real(FilteredWhiteNoise);

                # Sound reproduction
                print("Reproducing sound\n");
                sd.play(FilteredWhiteNoise,fs, blocking=True);
                sd.wait();
                print("Sound reproducted\n");
                print(f"Amplitude = {amplitude}");
                print(f"Freq min = {minFreqCut}");
                print(f"Freq max = {maxFreqCut}");

                print("Did you hear the sound? (y/n)");
                text = input();

                if text == "y":
                    imperceptible = False;
                    return 20*np.log10(np.sqrt(np.mean(np.power(Noise,2)))); # Obtain RMS of the audio signal
                else:
                    amplitude+=0.0002;
        
        def obtain_db_border_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq):
            imperceptible=True;
            amplitude=0.001;
            while imperceptible:
                # White Noise
                nSamples = duration*fs;
                noise = amplitude*2*(np.random.rand(nSamples)-0.5);

                # Fourier Transform
                Noise = sp.fftshift(sp.fft(noise));

                # Filtering
                bpf = [1 if (abs(i)>=minFreqCut and abs(i)<=maxFreqCut) else 0 for i in np.linspace(-maxFreq, maxFreq, num=len(Noise))]; # BandPass filter
                FilteredWhiteNoise = np.multiply(Noise,bpf);

                # Inverse Transform
                FilteredWhiteNoise = sp.ifft(sp.ifftshift(FilteredWhiteNoise));
                FilteredWhiteNoise = np.real(FilteredWhiteNoise);

                # Sound reproduction
                print("Reproducing sound\n");
                sd.play(FilteredWhiteNoise,fs, blocking=True);
                sd.wait();
                print("Sound reproducted\n");
                print(f"Amplitude = {amplitude}");
                print(f"Freq min = {minFreqCut}");
                print(f"Freq max = {maxFreqCut}");

                print("Did you hear the sound? (y/n)");
                text = input();

                if text == "y":
                    imperceptible = False;
                    return 20*np.log10(np.sqrt(np.mean(np.power(Noise,2)))); # Obtain RMS of the audio signal
                else:
                    amplitude+=0.002;

        # Obtain user parameter
        nFBands = minimal.args.number_fft_bands;

        if nFBands==-1:
            return super().calculate_quantization_steps(max_q);

        # White noise properties
        duration = 2;
        fs = 44100;
        maxFreq = fs/2;

        # Decibels array
        SPLs = [];

        # Establish increments
        BandWidth = maxFreq/(2**self.dwt_levels * nFBands);
        minFreqCut = 0;
        maxFreqCut = BandWidth;

        # Loop for the first wavelet band
        for j in range(nFBands):
            if maxFreqCut<=1300:
                SPLs.append(obtain_db_border_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq));
            else:
                SPLs.append(obtain_db_centered_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq));
            minFreqCut = maxFreqCut;
            maxFreqCut += BandWidth;

        # Loop for the second until penultimate band
        for i in range(self.dwt_levels-1):
            for j in range(nFBands):
                SPLs.append(obtain_db_centered_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq));
                minFreqCut = maxFreqCut;
                maxFreqCut += BandWidth;
            maxFreqCut += BandWidth;
            BandWidth*=2;  
        
        # Loop for the last wavelet band
        for j in range(nFBands):
            if minFreqCut>=16000:
                SPLs.append(obtain_db_border_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq));
            else:
                SPLs.append(obtain_db_centered_frequency(duration,fs,minFreqCut,maxFreqCut,maxFreq));
            minFreqCut = maxFreqCut;
            maxFreqCut += BandWidth;
        
        return obtain_qss(SPLs,max_q);

class Advance_Threshold__verbose(Advance_Threshold, Treshold__verbose):
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
        intercom = Advance_Threshold__verbose()
    else:
        intercom = Advance_Threshold()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()   