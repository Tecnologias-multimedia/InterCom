# Don't send empty bitplanes.
#
# The sender of the bitplanes adds, to the number of received
# bitplanes, the number of skipped (zero) bitplanes of the chunk
# sent. It is also considered that the signs bitplane cound be all
# positives, something that could happen when we send a mono signal
# using two channels or the number of samples/chunk is very small.

import struct
import numpy as np
from intercom import Intercom
from intercom_dfc import Intercom_DFC

if __debug__:
    import sys

class Intercom_empty(Intercom_DFC):

    def init(self, args):
        Intercom_DFC.init(self, args)
        self.skipped_bitplanes = [0]*self.cells_in_buffer

    def send_bitplane(self, indata, bitplane_number):
        bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
        if np.any(bitplane): 
            bitplane = bitplane.astype(np.uint8)
            bitplane = np.packbits(bitplane)
            message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, self.received_bitplanes_per_chunk[(self.played_chunk_number+1) % self.cells_in_buffer]+1, *bitplane)
            self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
        else:
            self.skipped_bitplanes[self.recorded_chunk_number % self.cells_in_buffer] += 1

    def send(self, indata):
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        self.NOBPTS = int(0.75*self.NOBPTS + 0.25*self.NORB)
        self.NOBPTS += self.skipped_bitplanes[(self.played_chunk_number+1) % self.cells_in_buffer]
        self.skipped_bitplanes[(self.played_chunk_number+1) % self.cells_in_buffer] = 0
        self.NOBPTS += 1
        if self.NOBPTS > self.max_NOBPTS:
            self.NOBPTS = self.max_NOBPTS
        last_BPTS = self.max_NOBPTS - self.NOBPTS - 1
        #self.send_bitplane(indata, self.max_NOBPTS-1)
        #self.send_bitplane(indata, self.max_NOBPTS-2)
        #for bitplane_number in range(self.max_NOBPTS-3, last_BPTS, -1):
        for bitplane_number in range(self.max_NOBPTS-1, last_BPTS, -1):
            self.send_bitplane(indata, bitplane_number)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

    def feedback(self):
        volume = "*"*(30-self.skipped_bitplanes[(self.played_chunk_number+1) % self.cells_in_buffer])
        sys.stderr.write(volume + '\n'); sys.stderr.flush()

if __name__ == "__main__":
    intercom = Intercom_empty()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
