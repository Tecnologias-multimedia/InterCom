# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom import Intercom
from intercom_buffer import Intercom_buffer
from intercom_bitplanes import Intercom_bitplanes

if __debug__:
    import sys

class Intercom_binaural(Intercom_bitplanes):

    def record_send_and_play(self, indata, outdata, frames, time, status):
        pass

if __name__ == "__main__":
    intercom = Intercom_binaural()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
