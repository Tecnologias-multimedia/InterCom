import pywt as wt
import math
import numpy as np
from intra_frame_decorrelation import Intra_frame_decorrelation__verbose as spatial
import minimal
import argcomplete

minimal.parser.add_argument("-pd", "--padding", type=int, default=2, help="Overlapped samples of one chunk over other")
minimal.parser.add_argument("-ld", "--levels_of_DWT", type=int, default=1, help="Number of levels of the DWT")
class Temporal_decorrelation(spatial):
    def __init__(self):
        super().__init__()                
        self.wavelet = 'haar'         
        self.padding = minimal.args.padding
        self.levels = minimal.args.levels_of_DWT
        self.last_samples = np.zeros((self.padding,2))
        
#    def get_coeffs_bitplanes(self):
#        random = np.random.randint(low=-32768, high=32767, size=self.frames_per_chunk)
#        coeffs = wt.wavedec(random, wavelet=self.wavelet, level=self.levels, mode=self.padding)
#        arr, self.slices = wt.coeffs_to_array(coeffs)
#        max = np.amax(arr)
#        min = np.amin(arr)
#        range = max - min
#        bitplanes = int(math.floor(math.log(range)/math.log(2)))
#        return bitplanes
    def pack(self,chunk_number,chunk):
        coefs = np.empty(chunk.shape, dtype=np.int32)
        
        decomposition_0 = wt.wavedec(chunk[:,0],self.wavelet, level=self.levels)
        decomposition_1 = wt.wavedec(chunk[:,1],self.wavelet, level=self.levels)
        
        coefs_0, slices = wt.coeffs_to_array(decomposition_0)
        coefs_1, slices = wt.coeffs_to_array(decomposition_1)
        
        coefs[:, 0] = np.rint(coefs_0).astype(np.int32)
        coefs[:, 1] = np.rint(coefs_1).astype(np.int32)
        
        packet_chunk = super().pack(chunk_number,coefs)
        return packet_chunk, slices
    
    def unpack(self,chunk):
        upacked_chunk = np.empty((minimal.args.frames_per_chunk,2),dtype=np.int32)
        reconstructed_chunk =np.empty((minimal.args.frames_per_chunk+(self.padding*2),2),dtype=np.int32)
        chunk_number,chunk = super().unpack(chunk)
        
        decomposition_0 =wt.array_to_coeffs(chunk[:,0],self.slices,output_format='wavedec')
        decomposition_1 =wt.array_to_coeffs(chunk[:,1],self.slices,output_format='wavedec')
        
        reconstructed_chunk[:, 0] = np.rint(wt.waverec(decomposition_0, self.wavelet)).astype(np.int16)
        reconstructed_chunk[:, 1] = np.rint(wt.waverec(decomposition_1, self.wavelet)).astype(np.int16)
        
        upacked_chunk = reconstructed_chunk[self.padding:(minimal.args.frames_per_chunk+self.padding)]
        return chunk_number,upacked_chunk
    
    def _record_send_and_play(self, indata, outdata, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        #Sacamos los primeros samples del siguiente chunk
        next_chunk = self.unbuffer_next_chunk()
        self.next_samples = next_chunk[: self.padding]
        
        #creamos el chunk extendido
        extended_chunk = np.concatenate([self.last_samples, indata, self.next_samples])
        
        packed_chunk,self.slices = self.pack(self.chunk_number, extended_chunk)
        
        self.send(packed_chunk)
        
        self.last_samples = next_chunk[minimal.args.frames_per_chunk-self.padding :]
        
        self.play_chunk(outdata, next_chunk)
    
if __name__ == "__main__":

    minimal.parser.description = __doc__
    argcomplete.autocomplete(minimal.parser)
    minimal.args = minimal.parser.parse_known_args()[0]
    intercom = Temporal_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        minimal.parser.exit(1)
