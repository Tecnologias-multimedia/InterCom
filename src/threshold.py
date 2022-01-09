#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import numpy as np
import pywt
import logging
import struct
import zlib
import math
import minimal
from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT as temp_DWT
from stereo_MST_coding_32 import Stereo_MST_Coding_32 as stereo32

class threshold(temp_DWT):
    #V1
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
       
        self.frecuencias = []
        for i in range(len(self.bandas)):
            self.frecuencias.append('0')
        self.cuant = []
        for i in range(len(self.bandas)):
            self.cuant.append('0')

    def analyze(self,chunk):
        self.frecuencia = 22050
        if(self.dwt_levels == 0):
            self.frecuencias[0] = self.frecuencia
        else:    
            for i in range(self.dwt_levels,-1,-1):
                if(i == self.dwt_levels):
                    self.frecuencias[i] = self.frecuencia/2 
                elif(self.bandas[i] == self.bandas[i+1]):
                    self.frecuencias[i] = self.frecuencia
                else:
                    self.frecuencias[i] = self.frecuencia/2 
                self.frecuencia = self.frecuencia/2
                self.cuant[i] = abs(int(3.64*(self.frecuencias[i]/1000)**(-0.8)-6.5*math.exp((-0.6)*(self.frecuencias[i]/1000-3.3)**2)+ 10**(-3)*(self.frecuencias[i]/1000)**4))

    
        return super().analyze(chunk)


    def synthesize(self, chunk_DWT):
        return super().synthesize(chunk_DWT)

    def quantize(self, chunk):
        acumulador = 0
        for i in range (len(self.bandas1)):
           chunk[acumulador: self.bandas1[i]] = (chunk[acumulador: self.bandas1[i]] / self.cuant[i]).astype(np.int32)
           acumulador += self.bandas1[i]
        
        return chunk
    
    def dequantize(self, quantized_chunk):
        '''Deadzone dequantizer.'''
        acumulador = 0
        for i in range (len(self.bandas1)):
           quantized_chunk[acumulador: self.bandas1[i]] = quantized_chunk[acumulador: self.bandas1[i]] * self.cuant[i]
           acumulador += self.bandas1[i]
        return quantized_chunk
        

from temporal_overlapped_DWT_coding import Temporal_Overlapped_DWT__verbose as temp_DWT__verbose
    
class threshold__verbose(threshold,temp_DWT__verbose):
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
        intercom = threshold__verbose()
    else:
        intercom = threshold()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()