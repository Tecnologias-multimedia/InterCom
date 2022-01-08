#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK


import numpy as np
import pywt
import logging
import struct
import zlib
import math


import minimal
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT as temp_no_DWT
from stereo_MST_coding_32 import Stereo_MST_Coding_32 as stereo32

class Temporal_Overlapped_DWT(temp_no_DWT):
    
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        
        self.overlaped_area_size = self.max_filters_length * (1 << self.dwt_levels)

        self.lista = []
        for i in range(3):
            self.lista.append(np.zeros((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32))
            
        
       
        self.bandas1 = []
        aux =pywt.wavedecn_shapes((1024,), wavelet= self.wavelet, level=self.dwt_levels, mode='per')
        
        self.bandas1.extend(aux[0])
        for i in range(1,len(aux)):
            self.bandas1.extend(list(aux[i].values()))
            self.bandas1[i] = self.bandas1[i][0]
    

        
    def analyze(self,chunk):
        self.lista[0] = self.lista[1]
        self.lista[1] = self.lista[2]        
        self.lista[2] = chunk
       
        e = np.concatenate((self.lista[0][-self.overlaped_area_size:], self.lista[1], self.lista[2][:self.overlaped_area_size]))
        d= self._analyze(e)
        tam = int(len(d)/2)
        
        self.bandas = []
        aux =pywt.wavedecn_shapes((len(d),), wavelet=self.wavelet, level=self.dwt_levels, mode='per')
        
        self.bandas.extend(aux[0])
        for i in range(1,len(aux)):
            self.bandas.extend(list(aux[i].values()))
            self.bandas[i] = self.bandas[i][0]           
        

        valores = int((self.bandas[0]-self.bandas1[0])/2)
        reduced_d = d[0: self.bandas[0]][valores : -valores]
        acumulador = 0
        for i in range(1,self.dwt_levels+1):
            valores = int((self.bandas[i]-self.bandas1[i])/2)
            if(i == self.dwt_levels):
                reduced_d = np.concatenate((reduced_d,d[tam : ][valores:-valores]))
            else:
                reduced_d = np.concatenate((reduced_d,d[acumulador : acumulador+self.bandas[i]][valores : -valores]))
                acumulador += self.bandas[i]
        
        print(reduced_d.max(), reduced_d.min())
        return reduced_d
       
    def _analyze(self, chunk):
        chunk = stereo32.analyze(self, chunk)

        DWT_chunk = np.empty((minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk
    
    '''
    def synthesize(self, chunk_DWT):
        descom = [] #Descomposicion
        for i in range(3):
            descom.append(np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32))
        
            
        descom[0] = descom[1]
        descom[1] = descom[2]
        descom[2] = chunk_DWT
                    
                    
        extendido = np.array(descom[0][-self.overlaped_area_size : ][0: self.bandas1[0]])
        acumulado = 0
        for i in range (len(self.bandas1)):    
            if(i == 0):
                extendido = np.concatenate((extendido, descom[1][0 : self.bandas1[i]]))
                extendido = np.concatenate((extendido, descom[2][ : self.overlaped_area_size][0 : self.bandas1[i]]))
                acumulado += self.bandas1[i]
            elif (i == (len(self.bandas1)-1)):
                extendido = np.concatenate((extendido,descom[0][-self.overlaped_area_size : ][self.bandas1[i] : ]))
                extendido = np.concatenate((extendido,descom[1][self.bandas1[i] : ]))
                extendido = np.concatenate((extendido,descom[2][ : self.overlaped_area_size][self.bandas1[i] : ]))
            else:
                extendido = np.concatenate((extendido,descom[0][-self.overlaped_area_size : ][acumulado : acumulado+self.bandas1[i]]))
                extendido = np.concatenate((extendido,descom[1][acumulado : acumulado+self.bandas1[i]]))
                extendido = np.concatenate((extendido,descom[2][ : self.overlaped_area_size][acumulado : acumulado+self.bandas1[i]]))
                acumulado += self.bandas1[i]
        

        chunk = self._synthesize(extendido) 
       
       
        return chunk
    
    
    def _synthesize(self, chunk_DWT):
         chunk = np.empty((minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
         # Structure used during the decoding
         zero_array = np.zeros(shape=minimal.args.frames_per_chunk+2*self.overlaped_area_size)
         coeffs = pywt.wavedec(zero_array, wavelet=self.wavelet, level=self.dwt_levels, mode="per")
         slices = pywt.coeffs_to_array(coeffs)[1]
         for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], slices, output_format="wavedec")
            #chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(np.int32)
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
         chunk = stereo32.synthesize(self,chunk)
         return chunk[self.overlaped_area_size : -self.overlaped_area_size]
    
    '''
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT__verbose as temp_no_DWT__verbose

class Temporal_Overlapped_DWT__verbose(Temporal_Overlapped_DWT,temp_no_DWT__verbose):
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
        intercom = Temporal_Overlapped_DWT__verbose()
    else:
        intercom = Temporal_Overlapped_DWT()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()


