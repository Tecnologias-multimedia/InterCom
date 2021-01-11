#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Real-time Audio Intercommunicator (removes temporal redundancy).

    Applies wavelet to each subband obtained by the MST in order
    to remove temporal decorrelation and increase the ratio
    compression (and improve the quality reducing the RMSE)
'''

import numpy as np
import sounddevice as sd
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
import pywt

minimal.parser.add_argument("-w", "--wavelet_method", type=str, default="sym5", help="Wavelet name")
minimal.parser.add_argument("-wl", "--wavelet_dec_level", type=int, default=4, help="Wavelet decomposition level")
minimal.parser.add_argument("-aw", "--activate_wavelet", type=int, default=1, help="Wavelet decomposition level")

class Wavelet:
    """
    Class used to manage wavelet parameters
    """
    DEFAULT_WAVELET = "db10"
    DEFAULT_WAVELET_SIMPLE = "db10"

    def __init__(self, data_length, level=1, wavelet_name=DEFAULT_WAVELET):
        self.wavelet_name = wavelet_name
        print("Wavelet: ", wavelet_name)

        if (data_length < 0):
            data_length = -data_length
        if (data_length == 0):
            data_length += 1

        if (level == 0):
            level = 1
        if (level < 0):
            level = -level

        self.wavelet = pywt.Wavelet(wavelet_name)
        self.max_level = pywt.dwt_max_level(data_len=data_length, filter_len=self.wavelet.dec_len)
        self.level = level

        if (level > self.max_level):
            self.level = self.max_level
        print("Wavelet decomposition level:", self.level)
        self.number_of_overlapped_samples = 1 << math.ceil(math.log(self.wavelet.dec_len * self.level) / math.log(2))


class Temporal_decorrelate(br_control.BR_Control):
    ''' Temporal_decorrelate allows to remove the temporal
    redundancy in each band obtained by the MST.

    Due the fact that the MST is applied before de DWT, the class
    must inherit from br_control.
    '''

    def __init__(self):
        """
        Initializes the instance by generating the needed vectors
        to supress the error gaps and establish the variables used
        to generate the wavelet. It also calls the parent class.
        """
        super().__init__()

        # Three positional chunks to solve overlapping gaps
        self.central_chunk = np.zeros(shape=(minimal.args.frames_per_chunk, minimal.Minimal.NUMBER_OF_CHANNELS),
                                      dtype=np.int16)
        self.left_chunk = np.zeros(shape=(minimal.args.frames_per_chunk, minimal.Minimal.NUMBER_OF_CHANNELS),
                                   dtype=np.int16)
        self.right_chunk = np.zeros(shape=(minimal.args.frames_per_chunk, minimal.Minimal.NUMBER_OF_CHANNELS),
                                    dtype=np.int16)
        self.sender_buffer = []
        self.receiver_buffer = []
        # Generate the wavelet. Just check if the parameters are correct
        self.wavelet = Wavelet(minimal.args.frames_per_chunk, minimal.args.wavelet_dec_level,
                               minimal.args.wavelet_method)
        self.slice_send = []
        self.slice_receive = []

        print("Number of overlapped samples", self.wavelet.number_of_overlapped_samples)

    def DWT_analyze(self, x, levels, wavelet_name="db10"):
        """
        Applies the Discrete Wavelet and returns a numpy array and
        the slices needed to undo the wavelet.
        """

        coefs = np.empty(x.shape, dtype=np.int32)
        wavelet = pywt.Wavelet(wavelet_name)
        decomposition_0 = pywt.wavedec(x[:, 0], wavelet=wavelet, level=levels, mode="per")
        decomposition_1 = pywt.wavedec(x[:, 1], wavelet=wavelet, level=levels, mode="per")
        coefs_0, slices1 = pywt.coeffs_to_array(decomposition_0)
        coefs_1, slices2 = pywt.coeffs_to_array(decomposition_1)
        coefs[:, 0] = np.rint(coefs_0).astype(np.int32)
        coefs[:, 1] = np.rint(coefs_1).astype(np.int32)
        self.slice_receive = self.slice_send = slices1
        return coefs, slices1

    def DWT_synthesize(self, coefs, slices, wavelet_name="db10"):
        """
        Returns the original array from a numpy array that contains the
        wavelet coefficients.
        """
        wavelet = pywt.Wavelet(wavelet_name)
        samples = np.empty(coefs.shape, dtype=np.int32)
        decomposition_0 = pywt.array_to_coeffs(coefs[:, 0], slices, output_format="wavedec")
        decomposition_1 = pywt.array_to_coeffs(coefs[:, 1], slices, output_format="wavedec")
        samples[:, 0] = np.rint(pywt.waverec(decomposition_0, wavelet=wavelet, mode="per")).astype(np.int32)
        samples[:, 1] = np.rint(pywt.waverec(decomposition_1, wavelet=wavelet, mode="per")).astype(np.int32)
        return samples

    def analyze(self, x):
        """
        Analyze method separates channels into subbands using MST
        This method has been provided.
        """
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1]
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1]
        return w

    def synthesize(self, w):
        """
        Synthesize method reconstruct channels using the subbands
        This method has been provided
        """
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = (w[:, 0] + w[:, 1]) / 2
        x[:, 1] = (w[:, 0] - w[:, 1]) / 2
        return x

    def quantize(self, chunk, dtype=np.int32):
        """
        Override the quantize method in increase the
        dynamic range.
        """
        quantized_chunk = np.round(chunk / self.quantization_step).astype(dtype)
        return quantized_chunk

    def pack(self, chunk_number, chunk):
        """
        Applies the MST and DWT and send the result to the parent
        method pack.
        """
        self.left_chunk = self.central_chunk
        self.central_chunk = self.right_chunk
        self.right_chunk = chunk

        left_samples = self.left_chunk[len(chunk) - self.wavelet.number_of_overlapped_samples:]
        right_samples = self.right_chunk[: self.wavelet.number_of_overlapped_samples]
        extended_chunk = np.concatenate([left_samples, self.central_chunk, right_samples])

        # 1 MST
        extended_chunk = self.analyze(extended_chunk)
        # 2 DWT
        extended_chunk, self.slice_send = self.DWT_analyze(extended_chunk, self.wavelet.level, self.wavelet.wavelet_name)
        # 3 Quantice -> br_control
        # 4 Compress -> Compress (called by br_control)
        extended_chunk = super().pack(chunk_number, extended_chunk)
        return extended_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        """
        Retrieves the pack from the parent unpack method and applies the
        synthesis methods to obtain the "original" chunk.
        """
        # 1 Decompress
        # 2 Dequantize
        chunk_number, extended_chunk = super().unpack(packed_chunk, np.int32)
        # 3 DWT
        extended_chunk = self.DWT_synthesize(extended_chunk, self.slice_send, self.wavelet.wavelet_name)
        # 4 MST
        extended_chunk = self.synthesize(extended_chunk)
        # 5 Retrieve central part
        chunk = extended_chunk[self.wavelet.number_of_overlapped_samples: len(extended_chunk) - self.wavelet.number_of_overlapped_samples]
        return chunk_number, chunk


class Temporal_decorrelate__verbose(Temporal_decorrelate, br_control.BR_Control__verbose):
    """
    Verbose class used to show data.
    """
    def __init__(self):
        super().__init__()


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
        intercom = Temporal_decorrelate__verbose()
    else:
        intercom = Temporal_decorrelate()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")






