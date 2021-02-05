#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (lossless compression of the chunks). '''

import numpy as np
import pywt
import pywt.data
import math
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import intra_frame_decorrelation

'''
pywavelets.readthedocs.io/en/latest/ref/dwt-discrete-wavelet-transform.html#maximum-decomposition-level-dwt-max-level-dwtn-max-level
'''

minimal.parser.add_argument("-n", "--number_of_levels", type=int, default=4, help="Number of levels")

class Temporal_decorrelation_simple(intra_frame_decorrelation.Intra_frame_decorrelation):
    def __init__(self):
        if __debug__:
            print("Running Temporal_decorrelation_simple.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (Temporal_decorrelation_simple) is running")
        self.levels = minimal.args.number_of_levels
        print("Number of levels =", minimal.args.number_of_levels)

        self.wavelet_name = "coif2"
        self.wavelet = pywt.Wavelet(self.wavelet_name)

        if(self.levels == 0):
            self.number_of_overlaped_samples = 0
        else:
            self.number_of_overlaped_samples = 1 << math.ceil(math.log(self.wavelet.dec_len * self.levels) / math.log(2))

        #print("Size current chunk:", self.current_chunk.shape)
        temp_chunk = super().generate_zero_chunk()
        temp_decomposition = pywt.wavedec(temp_chunk[:,0], wavelet=self.wavelet, level=self.levels, mode="per")
        temp_coefficients, self.slices = pywt.coeffs_to_array(temp_decomposition)
        
    def pack(self, chunk_number, chunk):
        decomposition_left = pywt.wavedec(chunk[:,0], wavelet=self.wavelet, level=self.levels, mode="per")
        coefficients_0, slices = pywt.coeffs_to_array(decomposition_left)
        decomposition_right = pywt.wavedec(chunk[:,1], wavelet=self.wavelet, level=self.levels, mode="per")
        coefficients_1, slices = pywt.coeffs_to_array(decomposition_right)        
        
        coefficients = np.empty_like(chunk, dtype=np.int32)
        coefficients[:, 0] = coefficients_0[:]
        coefficients[:, 1] = coefficients_1[:]
        return super().pack(chunk_number, coefficients)
        #TODO: elegir pywavelet.

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        decomposition_left = pywt.array_to_coeffs(chunk[:,0], self.slices, output_format="wavedec")
        decomposition_right = pywt.array_to_coeffs(chunk[:,1], self.slices, output_format="wavedec")
        reconstructed_chunk_left = pywt.waverec(decomposition_left, wavelet=self.wavelet, mode="per")
        reconstructed_chunk_right = pywt.waverec(decomposition_right, wavelet=self.wavelet, mode="per")
        reconstructed_chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=dtype)
        reconstructed_chunk[:, 0] = reconstructed_chunk_left[:]
        reconstructed_chunk[:, 1] = reconstructed_chunk_right[:]
        return chunk_number, reconstructed_chunk

class Temporal_decorrelation_simple__verbose(Temporal_decorrelation_simple, intra_frame_decorrelation.Intra_frame_decorrelation__verbose):
    pass

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
        intercom = Temporal_decorrelation_simple__verbose()
    else:
        intercom = Temporal_decorrelation_simple()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")