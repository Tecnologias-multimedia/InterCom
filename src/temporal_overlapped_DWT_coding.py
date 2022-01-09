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
    #V1
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        
        self.overlaped_area_size = self.max_filters_length * (1 << self.dwt_levels)

        self.lista = [] #Encoder
        for i in range(3):
            self.lista.append(np.zeros((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32))
            
                        
        self.descom = [] #Decoder
        for i in range(3):
            self.descom.append(np.zeros((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=np.int32))
        
       
        #BANDAS PARA 1024 (PERMITE CALCULAR SUBBANDAS)      
        self.bandas1 = []
        aux =pywt.wavedecn_shapes((1024,), wavelet= self.wavelet, level=self.dwt_levels, mode='per')
        
        self.bandas1.extend(aux[0])
        for i in range(1,len(aux)):
            self.bandas1.extend(list(aux[i].values()))
            self.bandas1[i] = self.bandas1[i][0]
        
        #BANDAS EXTENDIDAS (PERMITE CALCULAR SUBBANDAS)
        self.bandas = []
        aux =pywt.wavedecn_shapes((1024+2*self.overlaped_area_size,), wavelet=self.wavelet, level=self.dwt_levels, mode='per')
        
        self.bandas.extend(aux[0])
        for i in range(1,len(aux)):
            self.bandas.extend(list(aux[i].values()))
            self.bandas[i] = self.bandas[i][0]           
    
        
        #Coeficientes para extendido
        zero_array = np.zeros(shape=minimal.args.frames_per_chunk+2*self.overlaped_area_size)
        coeffs = pywt.wavedec(zero_array, wavelet=self.wavelet, level=self.dwt_levels, mode="per")
        self.slices = pywt.coeffs_to_array(coeffs)[1]
        

        
        
    def analyze(self,chunk):
                               
        self.lista[2] = chunk
        e = np.concatenate((self.lista[0][-self.overlaped_area_size:], self.lista[1], self.lista[2][:self.overlaped_area_size]))
        d= self._analyze(e)
        
       
                
        reduced_d = d[0: self.bandas[0]][self.overlaped_area_size//2**self.dwt_levels : -self.overlaped_area_size//2**self.dwt_levels]
                    
        acumulador= self.bandas[0]
        for i in range(self.dwt_levels):
            if(i == self.dwt_levels-1):
                reduced_d = np.concatenate((reduced_d,d[acumulador : acumulador+self.bandas[i+1]][self.overlaped_area_size//2 : -self.overlaped_area_size//2]))
            else:
                reduced_d = np.concatenate((reduced_d,d[acumulador : acumulador+self.bandas[i+1]][self.overlaped_area_size//2**(self.dwt_levels-i) : -self.overlaped_area_size//2**(self.dwt_levels-i)]))
                acumulador += self.bandas[i+1]
            
          
                
        self.lista[0] = self.lista[1]
        self.lista[1] = self.lista[2]
        return reduced_d

    def _analyze(self, chunk):
        chunk = stereo32.analyze(self,chunk)
        DWT_chunk = np.zeros((minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk
    
    
    def synthesize(self, chunk_DWT):
            
        self.descom[2] = chunk_DWT
        
        division = int(self.overlaped_area_size/(2**(self.dwt_levels)))
        extendido = np.array(self.descom[0][0: self.bandas1[0]][-division: ])
        acumulado = 0
        
        for i in range (self.dwt_levels+1):
            if(i == 0):
                extendido = np.concatenate((extendido, self.descom[1][0 : self.bandas1[i]]))
                extendido = np.concatenate((extendido, self.descom[2][0 : self.bandas1[i]][ : division]))
                acumulado += self.bandas1[i]
                
            elif (i == self.dwt_levels):
                division = int(self.overlaped_area_size/2)
                extendido = np.concatenate((extendido,self.descom[0][self.bandas1[i] : ][-division : ]))
                extendido = np.concatenate((extendido,self.descom[1][self.bandas1[i] : ]))
                extendido = np.concatenate((extendido,self.descom[2][self.bandas1[i] : ][ : division]))
            else:
                division = int(self.overlaped_area_size/(2**(self.dwt_levels-(i-1))))
                extendido = np.concatenate((extendido,self.descom[0][acumulado : acumulado+self.bandas1[i]][-division : ]))
                extendido = np.concatenate((extendido,self.descom[1][acumulado : acumulado+self.bandas1[i]]))
                extendido = np.concatenate((extendido,self.descom[2][acumulado : acumulado+self.bandas1[i]][ : division]))
                acumulado += self.bandas1[i]

        chunk = self._synthesize(extendido)
        

        chunkfinal = chunk[self.overlaped_area_size : -self.overlaped_area_size]
        
        self.descom[0] = self.descom[1]
        self.descom[1] = self.descom[2]
        
        return chunkfinal
      
    def _synthesize(self, chunk_DWT):
        chunk = np.zeros((minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)          
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            #chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(np.int32)
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        chunk= stereo32.synthesize(self,chunk)
        return chunk   
    
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT__verbose as temp_no_DWT__verbose
    
   
class Temporal_Overlapped_DWT__verbose(Temporal_Overlapped_DWT,temp_no_DWT__verbose):
     def compute(self, indata, outdata):
        # Remember that indata contains the recorded chunk and
        # outdata, the played chunk, but this is only true after
        # running this method.
        
        self.recorded_chunks_buff[self.chunk_number % self.cells_in_buffer] = indata.copy()
        recorded_chunk = self.recorded_chunks_buff[(self.chunk_number - self.chunks_to_buffer - 3) % (self.cells_in_buffer)].astype(np.double) #CAMBIO PARA DELAY
        played_chunk = outdata.astype(np.double)

        if minimal.args.show_samples:
            print("\033[32mbr_control: ", end=''); self.show_indata(recorded_chunk.astype(np.int))
            print("\033[m", end='')
            # Remember that
            # buffer.Buffering__verbose._record_io_and_play shows also
            # indata and outdata.
        
            print("\033[32mbr_control: ", end=''); self.show_outdata(played_chunk.astype(np.int))
            print("\033[m", end='')

        square_signal = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            square_signal[c] = recorded_chunk[:, c] * recorded_chunk[:, c]
        # Notice that numpy uses the symbol "*" for computing the dot
        # product of two arrays "a" and "b", that basically is the
        # projection of one of the vectors ("a") into the other
        # ("b"). However, when both vectors are the same and identical
        # in shape (np.arange(10).reshape(10,1) and
        # np.arange(10).reshape(1,10) are the same vector, but one is
        # a row matrix and the other is a column matrix) and the
        # contents are the same, the resulting vector is the result of
        # computing the power by 2, which is equivalent to compute
        # "a**2". Moreover, numpy provides the element-wise array
        # multiplication "numpy.multiply(a, b)" that when "a" and "b"
        # are equal, generates the same result. Among all these
        # alternatives, the dot product seems to be the faster one.
       
        signal_energy = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            signal_energy[c] = np.sum( square_signal[c] )
 
        # Compute distortions
        error_signal = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            error_signal[c] = recorded_chunk[:, c] - played_chunk[:, c]
            
        square_error_signal = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            square_error_signal[c] = error_signal[c] * error_signal[c]
            
        error_energy = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            error_energy[c] = np.sum( square_error_signal[c] )

        RMSE = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            RMSE[c] = math.sqrt( error_energy[c] )
            self.accumulated_RMSE_per_cycle[c] += RMSE[c]

        SNR = [None] * self.NUMBER_OF_CHANNELS
        for c in range(self.NUMBER_OF_CHANNELS):
            if error_energy[c].any():
                if signal_energy[c].any():
                    SNR[c] = 10.0 * math.log( signal_energy[c] / error_energy[c] )
                    self.accumulated_SNR_per_cycle[c] += SNR[c]

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