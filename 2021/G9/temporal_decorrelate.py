import numpy as np
import sounddevice as sd
import pywt
import math
import array
import itertools
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
            print("Running Temporal_decorrelation.__init__")
        filters_name = "db5"
        self.wavelet = pywt.Wavelet(filters_name)
        self.levels = 3
        self.signal_mode_extension = "per"
        self.precision_type = np.int32
        super().__init__()
        
    def dequantize_and_detransform(self,decomposition):
        dequantized_decomposition = []
        for subband in decomposition:
            dequantized_subband = self.dequantize(subband)
            dequantized_decomposition.append(dequantized_subband)
        chunk = pywt.waverec(dequantized_decomposition, wavelet=self.wavelet, mode=self.signal_mode_extension)
        return chunk

    def reconstruct_chunk(self,chunk):
        quantization_indexes = transform_and_quantize(chunk)
        reconstructed_chunk = dequantize_and_detransform(quantization_indexes)
        return reconstructed_chunk
    
    def pack(self, chunk_number, chunk):
        decomposition = pywt.wavedec(chunk, wavelet=self.wavelet, level=self.levels, mode=self.signal_mode_extension)
        quantized_decomposition = []
        for subband in decomposition:
            quantized_subband = self.quantize(subband)
            quantized_decomposition.append(quantized_subband)
        packed_chunk = super().pack(chunk_number, quantized_decomposition)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, quantized_decomposition = super().unpack(packed_chunk, dtype)
        chunk = self.dequantize_and_detransform(quantized_decomposition)
        reconstruct= self.reconstruct_chunk(chunk);
        return reconstruct

class Temporal_decorrelation__verbose(Temporal_decorrelation, intra_frame_decorrelation.Intra_frame_decorrelation__verbose):
    def __init__(self):
        super().__init__()
        self.LH_variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_LH_variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.LH_chunks_in_the_cycle = []

    def stats(self):
        string = super().stats()
        #string += " {}".format(['{:>5d}'.format(int(i/1000)) for i in self.LH_variance])
        return string

    def _first_line(self):
        string = super().first_line()
        #string += "{:19s}".format('') # LH_variance
        return string

    def first_line(self):
        string = super().first_line()
        #string += "{:19s}".format('') # LH_variance
        return string

    def second_line(self):
        string = super().second_line()
        #string += "{:>19s}".format("LH variance") # LH variance
        return string

    def separator(self):
        string = super().separator()
        #string += f"{'='*19}"
        return string

    def averages(self):
        string = super().averages()
        #string += " {}".format(['{:>5d}'.format(int(i/1000)) for i in self.average_LH_variance])
        return string

    def cycle_feedback(self):
        try:
            concatenated_chunks = np.vstack(self.LH_chunks_in_the_cycle)
            self.LH_variance = np.var(concatenated_chunks, axis=0)
        except ValueError:
            pass
        self.average_LH_variance = self.moving_average(self.average_LH_variance, self.LH_variance, self.cycle)
        super().cycle_feedback()
        self.LH_chunks_in_the_cycle = []

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
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Temporal_decorrelation__verbose()
    else:
        intercom = Temporal_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
