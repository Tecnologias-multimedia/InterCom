# Implementing a Data-Flow Control algorithm.

import struct
import numpy as np
from intercom import Intercom
from intercom_binaural import Intercom_binaural

if __debug__:
    import sys

class Intercom_dfc(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.packet_format = f"!HBB{self.frames_per_chunk//8}B"
        self.received_bitplanes_per_chunk = [0]*self.cells_in_buffer
        self.max_nobpts = 16*self.number_of_channels
        self.number_of_bitplanes_to_send = self.max_nobpts
        self.nobpts = self.number_of_bitplanes_to_send

    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, self.number_of_bitplanes_to_send, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(np.uint16)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number%self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        return received_chunk_number

    def send_bitplane(self, indata, bitplane_number):
        bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
        bitplane = bitplane.astype(np.uint8)
        bitplane = np.packbits(bitplane)
        message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, self.received_bitplanes_per_chunk[(self.played_chunk_number+1) % self.cells_in_buffer]+1, *bitplane)
        self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))
    
    def feedback(self):
        sys.stderr.write(str(self.number_of_bitplanes_to_send) + " "); sys.stderr.flush()

    def record_and_send(self, indata):
        #signs = indata >> 15
        #magnitudes = abs(indata)
        #indata = (signs << 15) | magnitudes
        
        self.nobpts = int(0.9*self.pnobts+0.1*self.number_of_bitplanes_to_send)
        self.nobpts += 1
        if self.nobpts > self.max_nobpts:
            self.nobpts = self.max_nobpts
        last_bpts = self.max_nobpts - self.self.nobpts - 1
        #print(self.number_of_bitplanes_to_send, last_bitplane_to_send)
        self.send_bitplane(indata, self.max_nobpts-1)
        self.send_bitplane(indata, self.max_nobpts-2)
        for bitplane_number in range(self.max_nobpts-3, last_bpts, -1):
            self.send_bitplane(indata, bitplane_number)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        #Intercom_binaural.record_and_send(self, indata)

    def play(self, indata):
        Intercom_binaural.play(self, indata)
        self.received_bitplanes_per_chunk [self.played_chunk_number % self.cells_in_buffer] = 0
        print(*self.received_bitplanes_per_chunk)

if __name__ == "__main__":
    intercom = Intercom_dfc()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
