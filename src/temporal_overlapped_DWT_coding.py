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
           
        
    def analyze(self,chunk):             
        self.lista[0] = self.lista[1]
        self.lista[1] = self.lista[2]
        self.lista[2] = chunk
        e = np.concatenate((self.lista[0][-self.overlaped_area_size:], self.lista[1], self.lista[2][:self.overlaped_area_size]))
        d= self._analyze(e)
        low_freq = d[0:int(len(d)/4)]
        high_freq2 = d[int(len(d)/4): int(len(d)/2)]
        high_freq1 = d[int(len(d)/2):]
        valores = int(self.overlaped_area_size/pow(2,self.dwt_levels));        
        
        reduced_d = np.concatenate((low_freq[valores:-valores],high_freq2[valores:-valores], high_freq1[valores:-valores]), axis = 0)
        return reduced_d;
       
    
        #d[2][(self.overlaped_Area_size/(pow(2,self.dwt_levels-1)): -(self.overlaped_Area_size/(pow(2,self.dwt_levels-1))))])
    def _analyze(self, chunk):
        chunk = stereo32.analyze(self, chunk)

        DWT_chunk = np.empty((minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk
            
    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHH", packed_chunk[:6])
        offset = 6 # Header size
        compressed_MSB1 = packed_chunk[offset : len_compressed_MSB1 + offset]
        offset += len_compressed_MSB1 
        compressed_MSB0 = packed_chunk[offset : len_compressed_MSB0 + offset]
        offset += len_compressed_MSB0 
        compressed_LSB = packed_chunk[offset :]
        buffer_MSB1 = zlib.decompress(compressed_MSB1)
        buffer_MSB0 = zlib.decompress(compressed_MSB0)
        buffer_LSB  = zlib.decompress(compressed_LSB)
        channel_MSB1 = np.frombuffer(buffer_MSB1, dtype=np.int8)
        channel_MSB0 = np.frombuffer(buffer_MSB0, dtype=np.uint8)
        channel_LSB  = np.frombuffer(buffer_LSB, dtype=np.uint8)
        valores = int(self.overlaped_area_size/pow(2,self.dwt_levels));
        print(valores)
        chunk = np.empty((minimal.args.frames_per_chunk+3*valores, 2), dtype=np.int32)
        chunk[:, 0] = channel_MSB1[:len(channel_MSB1)//2]*(1<<16) + channel_MSB0[:len(channel_MSB0)//2]*(1<<8) + channel_LSB[:len(channel_LSB)//2]
        chunk[:, 1] = channel_MSB1[len(channel_MSB1)//2:]*(1<<16) + channel_MSB0[len(channel_MSB0)//2:]*(1<<8) + channel_LSB[len(channel_LSB)//2:]

        return chunk_number, chunk
    
    
    def play_chunk(self, DAC, chunk):
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        chunk = chunk.reshape(minimal.args.frames_per_chunk+2*self.overlaped_area_size, self.NUMBER_OF_CHANNELS)
        DAC[:] = chunk

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


