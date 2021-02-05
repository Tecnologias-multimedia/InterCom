import minimal
import spatial
import struct
import pywt
import numpy as np
import math

class Temporal_decorrelation(spatial.Intra_frame_decorrelation__verbose):
    levels = 3           # Number of levels of the DWT
    filters_name = "db5"
    wavelet = pywt.Wavelet(filters_name)
    signal_mode_extension = "per"
    quantization_step = 256
    chunk_size = 1024
    chunk_number = 15
    number_of_overlaped_samples = 1 << math.ceil(math.log(wavelet.dec_len * levels) / math.log(2))

    def deadzone_quantizer(self,x, quantization_step):
        k = (x / quantization_step).astype(np.int)
        return k

    def deadzone_dequantizer(self,k, quantization_step):
        y = quantization_step * k
        return y

    def transform_and_quantize(self,chunk):
        decomposition = pywt.wavedec(chunk, wavelet=self.wavelet, level=self.levels, mode=self.signal_mode_extension)
        quantized_decomposition = []
        for subband in decomposition:
            quantized_subband = self.deadzone_quantizer(subband, self.quantization_step)
            quantized_decomposition.append(quantized_subband)
        return quantized_decomposition
    
    def dequantize_and_detransform(self,decomposition):
        dequantized_decomposition = []
        for subband in decomposition:
            dequantized_subband = self.deadzone_dequantizer(subband, self.quantization_step)
            dequantized_decomposition.append(dequantized_subband)
        chunk = pywt.waverec(dequantized_decomposition, wavelet=self.wavelet, mode=self.signal_mode_extension)
        return chunk

    def reconstruct_chunk(self,chunk):
        quantization_indexes = self.transform_and_quantize(chunk)
        reconstructed_chunk = self.dequantize_and_detransform(quantization_indexes)
        return reconstructed_chunk
    
    def pack(self, chunk_number, chunk):
        left_chunk = self._buffer[(chunk_number-1)%self.cells_in_buffer]
        center_chunk = chunk
        right_chunk = self._buffer[(chunk_number+1)%self.cells_in_buffer]
        last_samples_left_chunk = left_chunk[self.chunk_size - self.number_of_overlaped_samples :]
        first_samples_right_chunk = right_chunk[: self.number_of_overlaped_samples]
        extended_chunk = np.concatenate([last_samples_left_chunk, center_chunk, first_samples_right_chunk])
        packed_chunk = self._pack(chunk_number, self.transform_and_quantize(extended_chunk))
        return packed_chunk
    
    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, chunk = self._unpack(packed_chunk, dtype)
        chunk = self.dequantize_and_detransform(chunk)
        return chunk_number, chunk

    def _pack(self, chunk_number, chunk):
        print(np.array(chunk).shape)
        packed_chunk = struct.pack("!H", chunk_number) + np.array(chunk).tobytes()
        return packed_chunk

    def _unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        chunk = packed_chunk[2:]
        chunk = np.frombuffer(chunk, dtype=dtype)
        chunk = chunk.reshape(8704, 1)
        chunk = chunk.tolist()
        lista = []
        lista.append(np.array(chunk[0:1088]))
        lista.append(np.array(chunk[0:1088]))
        lista.append(np.array(chunk[0:1088]))
        lista.append(np.array(chunk[0:1088]))
        return chunk_number, chunk
    
if __name__ == "__main__":
    minimal.parser.description = __doc__
    minimal.args = minimal.parser.parse_args()
    intercom = Temporal_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")