#
# Intercom_minimal
# |
# +- Intercom_buffer
#    |
#    +- Intercom_bitplanes
#       |
#       +- Intercom_binaural
#          |
#          +- Intercom_DFC
#             |
#             +- Intercom_empty
#                |
#                +- Intercom_DWT
#
# Convert the chunks of samples intro chunks of wavelet coefficients
# (coeffs in short).
#
# The coefficients require more bitplanes than the original samples,
# but most of the energy of the samples of the original chunk tends to
# be into a small number of coefficients that are localized, usually
# in the low-frequency subbands:
#
# (supposing a chunk with 1024 samples)
#
# Amplitude
#     |       +                      *
#     |   *     *                  *
#     | *        *                *
#     |*          *             *
#     |             *       *
#     |                 *
#     +------------------------------- Time
#     0                  ^        1023 
#                |       |       
#               DWT  Inverse DWT 
#                |       |
#                v
# Amplitude
#     |*
#     |
#     | *
#     |  **
#     |    ****
#     |        *******
#     |               *****************
#     +++-+---+------+----------------+ Frequency
#     0                            1023
#     ^^ ^  ^     ^           ^
#     || |  |     |           |
#     || |  |     |           +--- Subband H1 (16N coeffs)
#     || |  |     +--------------- Subband H2 (8N coeffs)
#     || |  +--------------------- Subband H3 (4N coeffs)
#     || +------------------------ Subband H4 (2N coeffs)
#     |+-------------------------- Subband H5 (N coeffs)
#     +--------------------------- Subband L5 (N coeffs)
#
# (each channel must be transformed independently)
#
# This means that the most-significant bitplanes, for most of the
# chunks (this depends on the content of the chunk), should have only
# bits different of 0 in the coeffs that belongs to the low-frequency
# subbands. This will be exploited in a future issue. In a future
# issue should be implemented also a subband weighting procedure in
# order to sent first the most energetic coeffs. Notice, however, that
# these subband weights depends on the selected wavelet.
#

import sounddevice as sd
import struct
import numpy as np
import pywt as wt
import math
#from intercom import Intercom
from intercom_empty import Intercom_empty

#if __debug__:
#    import sys
#    import time

class Intercom_DWT(Intercom_empty):

    def init(self, args):
        Intercom_empty.init(self, args)
        self.precision_bits = 32
        self.sample_type = np.int32
        self.sign_mask = (1<<(self.precision_bits-1))
        self.precision_bits_1 = self.precision_bits-1
        self.magnitude_mask = ((1<<(self.precision_bits_1))-1)
        self.number_of_bitplanes_to_send = self.precision_bits * self.number_of_channels
        if __debug__:
            print("intercom_dwt: number_of_bitplanes_to_send={}".format(self.number_of_bitplanes_to_send))
        self.max_number_of_bitplanes_to_send = self.number_of_bitplanes_to_send
        self.number_of_received_bitplanes = self.max_number_of_bitplanes_to_send
        self.levels = 4                  # Number of levels of the DWT
        self.wavelet = 'bior3.5'         # Wavelet Biorthogonal 3.5
        self.padding = "periodization"   # Signal extension procedure used in
        self.slices = self.get_coeffs_slices()
        print("intercom_dwt: using wavelet domain \"{}\"".format(self.wavelet))

    def get_coeffs_slices(self):
        zeros = np.zeros(shape=self.frames_per_chunk)
        coeffs = wt.wavedec(zeros, wavelet=self.wavelet, level=self.levels, mode=self.padding)
        return wt.coeffs_to_array(coeffs)[1]
        #arr, self.slices = wt.coeffs_to_array(coeffs)
        #max = np.amax(arr)
        #min = np.amin(arr)
        #range = max - min
        #bitplanes = int(math.floor(math.log(range)/math.log(2)))
        #return bitplanes

    def DWT(self, chunk):
        #return chunk
        coeffs_in_subbands = wt.wavedec(chunk, wavelet=self.wavelet, level=self.levels, mode=self.padding)
        return np.around(wt.coeffs_to_array(coeffs_in_subbands)[0]).astype(self.sample_type)

    def iDWT(self, coeffs_in_array):
        #return coeffs_in_array
        coeffs_in_subbands = wt.array_to_coeffs(coeffs_in_array, self.slices, output_format="wavedec")
        return np.around(wt.waverec(coeffs_in_subbands, wavelet=self.wavelet, mode=self.padding)).astype(self.sample_type)

    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:,1] -= indata[:,0]
        indata[:,0] = self.DWT(indata[:,0])
        signs = indata & self.sign_mask
        magnitudes = abs(indata)
        indata = signs | magnitudes
        self.send(indata)
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        signs = chunk >> self.precision_bits_1
        magnitudes = chunk & self.magnitude_mask
        chunk = magnitudes + magnitudes*signs*2
        chunk[:,0] = self.iDWT(chunk[:,0])
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = chunk
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,1] += self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0]
        self.play(outdata)
        self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer] = 0

    def record_send_and_play(self, indata, outdata, frames, time, status):
        #print(indata)
        indata[:,0] = self.DWT(indata[:,0])
        signs = indata & self.sign_mask
        magnitudes = abs(indata)
        indata = signs | magnitudes
        #print(indata)
        self.send(indata)
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        signs = chunk >> self.precision_bits_1
        magnitudes = chunk & self.magnitude_mask
        chunk = magnitudes + magnitudes*signs*2
        chunk[:,0] = self.iDWT(chunk[:,0])
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = chunk
        #print(chunk)
        self.play(outdata)
        if __debug__:
            self._number_of_received_bitplanes.value += self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer]
        self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer] = 0

if __name__ == "__main__":
    intercom = Intercom_DWT()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
