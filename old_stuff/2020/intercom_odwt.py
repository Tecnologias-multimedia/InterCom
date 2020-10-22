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
#                   |
#                   +- Intercom_WDWT
#                      |
#                      +- Intercom_ODWT
#
# This intercom considers the samples of adjacent chunks to compute
# the DWT. This should improve the correctness of the coefficients
# that are at the borders of each subband. Graphically:
#
#   chunk i-1     chunk i     chunk i+1
# +------------+------------+------------+
# |          OO|OOOOOOOOOOOO|OO          |
# +------------+------------+------------+
#
# O = sample
#
# The number of ajacent samples depends on the Wavelet transform (in
# the previous figure, only 2 samples from adjacent chunks have been
# used).
#
# Notice that only the coeffs of the chunk i must be transmitted when
# the chunk i is transmitted (the adjacent coeffs for all the
# resolution levels are ignored during the transmission).

import numpy as np
import pywt as wt
from intercom_wdwt import Intercom_WDWT

class Intercom_ODWT(Intercom_WDWT):

    def init(self, args):
        Intercom_WDWT.init(self, args)
        wavelet = wt.Wavelet(self.wavelet)
        self.number_of_overlapped_samples = wavelet.dec_len * self.levels
        self.extended_chunk_size = self.frames_per_chunk + self.number_of_overlapped_samples*2
        self.prev_chunk = np.zeros((self.frames_per_chunk,self.number_of_channels), dtype=np.int32)
        self.curr_chunk = np.zeros((self.frames_per_chunk,self.number_of_channels), dtype=np.int32)
        self.next_chunk = np.zeros((self.frames_per_chunk,self.number_of_channels), dtype=np.int32)
        print("intercom_odwt: number_of_overlapped_samples={}".format(self.number_of_overlapped_samples))

    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.prev_chunk = self.curr_chunk
        self.curr_chunk = self.next_chunk
        self.next_chunk = indata
        extended_chunk = np.concatenate((self.prev_chunk[self.frames_per_chunk-self.number_of_overlapped_samples:], self.curr_chunk, self.next_chunk[:self.number_of_overlapped_samples]), axis=0)
        coeffs_in_subbands = wt.wavedec(extended_chunk[:,0], wavelet=self.wavelet, level=self.levels, mode=self.padding)
        nos = self.number_of_overlapped_samples
        for i in range(len(coeffs_in_subbands)-1, 0, -1):
            nos >>= 1
            coeffs_in_subbands[i] = coeffs_in_subbands[i][nos:len(coeffs_in_subbands[i])-nos]
            print(nos, len(coeffs_in_subbands[i])-nos) 
        coeffs_in_subbands[0] = coeffs_in_subbands[0][nos:len(coeffs_in_subbands[0])-nos]
        chunk = wt.coeffs_to_array(coeffs_in_subbands)[0].astype(self.precision_type)
        signs = chunk & self.sign_mask
        magnitudes = abs(chunk)
        chunk = signs | magnitudes
        chunk = chunk.reshape((self.frames_per_chunk,1))
        #print(chunk.shape)
        self.send(chunk)
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
    intercom = Intercom_ODWT()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
