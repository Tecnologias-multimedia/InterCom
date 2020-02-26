#
# Intercom
# |
# +- Intercom_buffer
#    |
#    +- Intercom_bitplanes
#
# Transmits the samples of the chunks by bitplanes (16, i.e., CD
# quality). The bitplanes are transmitted from the most significant
# one to the least significant, each in a different packet.

import sounddevice as sd
import numpy as np
import struct
from intercom import Intercom
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)
        self.packet_format = f"!HB{self.frames_per_chunk//8}B"
        self.precision_bits = 16
        self.precision_type = np.int16
        self.number_of_bitplanes_to_send = self.precision_bits*self.number_of_channels
        print("transmitting by bitplanes")

    # Now, each packet transports a bitplane of a chunk. Again, this
    # is a blocking method that waits for a bitplane and inserts it
    # into a chunk. Both data (the bitplane number and the chunk
    # number) form the header. The bitplanes are packed using bytes.
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        received_chunk_number, received_bitplane_number, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(self.precision_type)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number % self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        return received_chunk_number

    # Sends a bitplane of the last recorded chunk (indata).
    def send_bitplane(self, indata, bitplane_number):
        bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
        bitplane = bitplane.astype(np.uint8)
        bitplane = np.packbits(bitplane)
        message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, *bitplane)
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    # Sends the last recorded chunk (indata).
    def send(self, indata):
        last_bitplane_to_send = self.precision_bits*self.number_of_channels - self.number_of_bitplanes_to_send
        for bitplane_number in range(self.precision_bits*2-1, last_bitplane_to_send, -1):
            self.send_bitplane(indata, bitplane_number)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
