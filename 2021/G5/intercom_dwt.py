
import struct
import sounddevice as sd
import numpy as np
import argparse
import socket
import pywt

import minimal
import buffer
import compress
import br_control
import intra_frame_decorrelation

if __debug__:
    import sys


class Intercom_dwt(intra_frame_decorrelation.Intra_frame_decorrelation):
    
    def __init__(self):
        super().__init__()
        self.actual = self.generate_zero_chunk()
        self.next = self.generate_zero_chunk()
        self.coeff_slices = 0

    def decompose(self, indata, chnl):
        #indata[:,chnl], coeff_slices = pywt.coeffs_to_array(pywt.wavedec(indata[:,chnl],  "bior3.5", "periodization")); return indata, coeff_slices
        left = self.actual[:,chnl]
        self.actual = self.next
        self.next = indata
        
        sending = np.copy(self.actual)
        coeff = pywt.wavedec(np.concatenate((left, self.actual[:,chnl], self.next[:,chnl]), axis=0),  "bior3.5", "periodization")
        sp = self.frames_per_chunk
        for i in range(len(coeff)-1, 0, -1):
            sp >>= 1
            coeff[i] = coeff[i][sp:len(coeff[i])-sp]
        coeff[0] = coeff[0][sp:len(coeff[0])-sp]
        sending[:,chnl], coeff_slices = pywt.coeffs_to_array(coeff)
        return sending, coeff_slices

    def recompose(self, data, coeff_slices, chnl):
        data[:,chnl] = np.around(pywt.waverec(pywt.array_to_coeffs(data[:,chnl]>>4, coeff_slices, output_format="wavedec"), "bior3.5", "periodization"))
        
    def pack(self, chunk_number, chunk):
        sending, self.coeff_slices = self.decompose(chunk, 1)
        packed_chunk = super().pack(chunk_number, sending)
        return packed_chunk
        
    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        '''Restores the original chunk representation.'''
        chunk_number, analyzed_chunk = super().unpack(packed_chunk, dtype)   
        self.recompose(analyzed_chunk, self.coeff_slices, 1)
        return chunk_number, analyzed_chunk

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
        intercom = Intercom_dwt()
    else:
        intercom = Intercom_dwt()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
