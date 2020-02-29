#
# Intercom
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
#

import sounddevice as sd
import struct
import numpy as np
import pywt as wt
import math
#from intercom import Intercom
from intercom_dwt import Intercom_DWT

if __debug__:
    import sys

class Intercom_WDWT(Intercom_DWT):

    def init(self, args):
        Intercom_DWT.init(self, args)
        zeros = np.zeros(self.frames_per_chunk)
        coeffs = wt.wavedec(zeros, wavelet=self.wavelet, level=self.levels, mode=self.padding)
        arr, slices = wt.coeffs_to_array(coeffs)
        energy = []
        subband = 0
        for i in range(self.levels,-1,-1):
            base = self.frames_per_chunk >> (i+1)
            base_div_2 = self.frames_per_chunk >> (i+2)
            coeff_index = base+base_div_2
            arr[coeff_index] = self.frames_per_chunk
            coeffs = wt.array_to_coeffs(arr, slices, output_format="wavedec")
            samples = wt.waverec(coeffs, wavelet=self.wavelet, mode=self.padding)
            arr[coeff_index] = 0
            energy.append(self.energy(samples))
            print("intercom_wdwt: coeff_index={} energy={}".format(coeff_index, energy[subband]))
            subband += 1
        min_energy = min(energy)
        print("intercom_mdwt: min_energy={}".format(min_energy))
        self.gain = []
        subband = 0
        for i in energy:
            self.gain.append(energy[subband] / min_energy)
            print("intercom_mdwt: gain[{}]={}".format(subband, self.gain[subband]))
            subband += 1

    # Energy of the signal x
    def energy(self, x):
        return np.sum(x*x)/len(x)


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
        #indata[:,0] = self.DWT(indata[:,0])
        coeffs_in_subbands = wt.wavedec(indata[:,0], wavelet=self.wavelet, level=self.levels, mode=self.padding)
        for i in range(len(coeffs_in_subbands)):
            #print(coeffs_in_subbands[i][0], self.gain[i])
            coeffs_in_subbands[i] *= self.gain[i]
        coeffs = wt.coeffs_to_array(coeffs_in_subbands)[0].astype(self.precision_type)
        signs = coeffs & self.sign_mask
        magnitudes = abs(coeffs)
        coeffs = signs | magnitudes
        self.send(coeffs.reshape((self.frames_per_chunk,1)))
        coeffs = self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0]
        signs = coeffs >> self.precision_bits_1
        magnitudes = coeffs & self.magnitude_mask
        coeffs = magnitudes + magnitudes*signs*2
        coeffs_in_subbands = wt.array_to_coeffs(coeffs.astype(np.float32), self.slices, output_format="wavedec")
        for i in range(len(coeffs_in_subbands)):
            #print(type(coeffs_in_subbands[i][0]), self.gain[i])
            coeffs_in_subbands[i] /= self.gain[i]
        chunk = np.around(wt.waverec(coeffs_in_subbands, wavelet=self.wavelet, mode=self.padding)).astype(self.precision_type)
        #chunk[:,0] = self.iDWT(chunk[:,0])
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0] = chunk
        #print(chunk)
        self.play(outdata)
        self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer] = 0

    def feedback(self):
        pass

if __name__ == "__main__":
    intercom = Intercom_WDWT()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
