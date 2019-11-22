# Implementing a Data-Flow Control algorithm.

import struct
import numpy as np
from intercom import Intercom
from intercom_binaural import Intercom_binaural

class Intercom_dfc(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.received_bitplanes_per_chunk = [0]*self.cells_in_buffer

    def receive_and_buffer(self):
        #received_chunk_number = Intercom_binaural.receive_and_buffer(self)
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.uint16)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number%self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        #print(self.received_bitplanes_per_chunk)
        return received_chunk_number

    def record_and_send(self, indata):
        #self.number_of_bitplanes_to_send = self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer]
        self.number_of_bitplanes_to_send = 3*self.number_of_channels
        Intercom_binaural.record_and_send(self, indata)
#    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
#        Intercom_binaural.record_send_and_play(self, indata, outdata, frames, time, status)
#        self.received_bitplanes_per_chunk [self.played_chunk_number % self.cells_in_buffer] = 0
        
if __name__ == "__main__":
    intercom = Intercom_dfc()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
