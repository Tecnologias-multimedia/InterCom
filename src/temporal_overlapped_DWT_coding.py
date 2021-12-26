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

        #self.previous_chunk = self.generate_zero_chunk
        self.lista = []
        for i in range(3):
            self.lista.append(np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32));
            
        self.bandas = []
        aux =pywt.wavedecn_shapes((1024,), wavelet='db2', level=self.dwt_levels, mode='per')
        
        for i in range(1,len(aux)):
            self.bandas.extend(list(aux[i].values()))
            
       
    
            
           
        
    def analyze(self,chunk):
            
        self.lista[0] = self.lista[1]
        self.lista[1] = self.lista[2]
        self.lista[2] = chunk
        e = np.concatenate((self.lista[0][-self.overlaped_area_size:], self.lista[1], self.lista[2][:self.overlaped_area_size]))
        d= self._analyze(e)
        reduced_d = []

        valores = int(self.overlaped_area_size/(pow(2,self.dwt_levels)))
        valores2 = int(self.overlaped_area_size/2)
        tam = len(d)/2

        
        for i in range(self.dwt_levels+1):
            if(i == self.dwt_levels):
                reduced_d.extend(np.array(d[int(tam):][valores2:-valores2]))
            else:                
                reduced_d.extend(np.array(d[(i)*(int(tam/self.dwt_levels)) : (i+1)*(int(tam/self.dwt_levels))][valores:-valores]))
                                    
        chunknuevo= np.array(reduced_d)
        return chunknuevo
       
    
    def _analyze(self, chunk):
        chunk = stereo32.analyze(self, chunk)

        DWT_chunk = np.empty((minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk
            
       


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


