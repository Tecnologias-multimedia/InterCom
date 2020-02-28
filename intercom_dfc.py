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
#
# Implements a Data-Flow Control algorithm.
#
# The receiver sends back (using piggybacking) the number of received
# bitplanes of each played chunk. The sender sends for the next chunk
# this number of bitplanes plus one. An weighted average is used to
# filter the fast changes in the link bandwidth. Sign-magnitude
# representation is used to minimize the distortion of the partially
# received negative samples.

import struct
import numpy as np
from intercom import Intercom
from intercom_binaural import Intercom_binaural

if __debug__:
    import sys

class Intercom_DFC(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.packet_format = f"!HBB{self.frames_per_chunk//8}B"
        self.received_bitplanes_per_chunk = [0]*self.cells_in_buffer
        #self.max_NOBPTS = self.precision_bits*self.number_of_channels  # Maximum Number Of Bitplanes To Send
        self.max_number_of_bitplanes_to_send = self.number_of_bitplanes_to_send
        if __debug__:
            print("intercom_dfc: max_number_of_bitplanes_to_send={}".format(self.max_number_of_bitplanes_to_send))
        #self.NOBPTS = self.max_NOBPTS
        #self.NORB = self.max_NOBPTS  # Number Of Received Bitplanes
        self.number_of_received_bitplanes = self.max_number_of_bitplanes_to_send 
        #self.precision_type = np.uint16
        print("intercom_dfc: controlling the data-flow")

    # Receives chunks, and now, in the header of each chunk, there
    # is the number of received bitplanes of the played chunk by the
    # intercolutor.
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_BYTES)
        received_chunk_number, received_bitplane_number, self.number_of_received_bitplanes, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(self.precision_type)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number%self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        return received_chunk_number

    # Now, for each sent bitplane, the number of received bitplanes,
    # for the chunk that has been played, is sent. This means that the
    # number of received bitplanes for each chunk is sent several
    # times, depending on the data-flow control.
    def send_bitplane(self, indata, bitplane_number):
        bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
        bitplane = bitplane.astype(np.uint8)
        bitplane = np.packbits(bitplane)
        message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, self.received_bitplanes_per_chunk[(self.played_chunk_number+1) % self.cells_in_buffer]+1, *bitplane)
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    # Implements the data-flow control: sends a number of bitplanes
    # which depends on the number of received bitplanes for the last
    # played chunk at the intercolutors side.
    def send(self, indata):
        self.number_of_bitplanes_to_send = int(0.75*self.number_of_bitplanes_to_send + 0.25*self.number_of_received_bitplanes)
        self.number_of_bitplanes_to_send += 1
        if self.number_of_bitplanes_to_send > self.max_number_of_bitplanes_to_send:
            self.number_of_bitplanes_to_send = self.max_number_of_bitplanes_to_send
        last_BPTS = self.max_number_of_bitplanes_to_send - self.number_of_bitplanes_to_send - 1
        self.send_bitplane(indata, self.max_number_of_bitplanes_to_send-1)
        self.send_bitplane(indata, self.max_number_of_bitplanes_to_send-2)
        for bitplane_number in range(self.max_number_of_bitplanes_to_send-3, last_BPTS, -1):
            self.send_bitplane(indata, bitplane_number)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

    # The new stuff represents the samples using the sign-magnitude
    # representation instead of the two's complement. This helps to
    # reconstruct the partially received chunks (when some bitplanes
    # are missing).
    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
        indata[:,1] -= indata[:,0]
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        self.send(indata)
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        signs = chunk >> 15
        magnitudes = chunk & 0x7FFF
        #chunk = ((~signs & magnitudes) | ((-magnitudes) & signs))
        chunk = magnitudes + magnitudes*signs*2
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = chunk
        self._buffer[self.played_chunk_number % self.cells_in_buffer][:,1] += self._buffer[self.played_chunk_number % self.cells_in_buffer][:,0]
        self.play(outdata)
        self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer] = 0
        #print(*self.received_bitplanes_per_chunk)

    # Mono version of the intercom.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        signs = indata & 0x8000
        magnitudes = abs(indata)
        indata = signs | magnitudes
        self.send(indata)
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        signs = chunk >> 15
        magnitudes = chunk & 0x7FFF
        chunk = magnitudes + magnitudes*signs*2
        self._buffer[self.played_chunk_number % self.cells_in_buffer]  = chunk
        self.play(outdata)
        self.received_bitplanes_per_chunk [self.played_chunk_number % self.cells_in_buffer] = 0

    def feedback(self):
        sys.stderr.write(str(self.number_of_bitplanes_to_send) + " "); sys.stderr.flush()

if __name__ == "__main__":
    intercom = Intercom_DFC()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
