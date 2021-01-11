import numpy as np
import sounddevice as sd
import pywt as wt
import math
import struct
import zlib
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import buffer
import compress
import br_control
import intra_frame_decorrelation

class Temporal_decorrelation(intra_frame_decorrelation.Intra_frame_decorrelation):
    def __init__(self):
        if __debug__:
            print("Running Intra_frame_decorrelation.__init__")
        filters_name = "db5"
        self.wavelet = wt.Wavelet(filters_name)
        self.levels = 3
        self.signal_mode_extension = "per"
        self.precision_type = np.int32        
        super().__init__()
        
    def pack(self, chunk_number, chunk):
        decomposition = self.DWT(chunk)
        quantized_decomposition = []
        for subband in decomposition:
            quantized_subband = self.quantize(subband)
            quantized_decomposition.append(quantized_subband)
        
        packed_chunk = super().pack(chunk_number, quantized_decomposition)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, decomposition = super().unpack(packed_chunk, dtype)
        
        dequantized_decomposition = []
        for subband in decomposition:
            dequantized_subband = self.dequantize(subband)
            dequantized_decomposition.append(dequantized_subband)
            
        dwted_chunk = iDWT(dequantized_decomposition)
        return chunk_number, dwted_chunk
    
    def DWT(self, chunk):
        return wt.wavedec(chunk, wavelet=self.wavelet, level=self.levels, mode=self.signal_mode_extension)
        #return np.around(wt.coeffs_to_array(coeffs_in_subbands)[0]).astype(self.precision_type)

    def iDWT(self, coeffs_in_array):
        return wt.array_to_coeffs(coeffs_in_array, wavelet=self.wavelet, mode=self.signal_mode_extension)
        #return np.around(wt.waverec(coeffs_in_subbands, wavelet=self.wavelet, mode=self.padding)).astype(self.precision_type)        

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_known_args()[0]
    intercom = Temporal_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")