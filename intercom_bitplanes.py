#
# Intercom
# |
# +- Intercom_buffer
#    |
#    +- Intercom_bitplanes
#
# Transmits the samples of the chunks by bitplanes. The bitplanes are
# transmitted from the most significant (15) one to the least
# significant (0), each in a different packet.
#
# The idea is to overwrite the methods of Intercom_buffer to send and
# receive by bit-planes.

from intercom_minimal import Intercom_minimal
from intercom_buffer import Intercom_buffer
import sounddevice as sd
import numpy as np
import struct

if __debug__:
    import sys
    import time
    from multiprocessing import Value

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        Intercom_buffer.init(self, args)
        self.packet_format = f"!HB{self.frames_per_chunk//8}B" # Quitar
        self.number_of_bitplanes = 16
        self.number_of_bitplanes_to_send = self.number_of_bitplanes * self.number_of_channels
        if __debug__:
            self.sent_messages_counter = Value('i', 0)
            self.received_messages_counter = Value('i', 0)
            self.sent_bytes_counter = Value('i', 0)
            self.received_bytes_counter = Value('i', 0)
            #self.total_sent = 0
            #self.total_received = 0
            #self.old_time = time.time()
        print("Intercom_bitplanes: transmitting by bitplanes")

    # Now, each packet transports a bitplane of a chunk. Again, this
    # is a blocking method that waits for a bitplane and inserts it
    # into a chunk. Both data (the bitplane number and the chunk
    # number) form the header. The bitplanes are packed using bytes.
    def receive_and_buffer(self):
        message, source_address = self.receive_message() #self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_BYTES)
        received_chunk_number, received_bitplane_number, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(self.sample_type)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number % self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        return received_chunk_number

    # Sends a bitplane of the last recorded chunk (indata).
    def send_bitplane(self, indata, bitplane_number):
        bitplane = (indata[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
        bitplane = bitplane.astype(np.uint8)
        bitplane = np.packbits(bitplane)
        message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, *bitplane)
        self.send_message(message)
        #self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    # Sends the last recorded chunk (indata).
    def send(self, indata):
        last_bitplane_to_send = self.number_of_bitplanes*self.number_of_channels - self.number_of_bitplanes_to_send
        for bitplane_number in range(self.number_of_bitplanes*2-1, last_bitplane_to_send, -1):
            self.send_bitplane(indata, bitplane_number)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER

    def send_message(self, chunk):
        super().send(chunk)
        if __debug__:
            self.sent_messages_counter.value += 1
            self.sent_bytes_counter.value += len(message)

    def receive_message(self):
        chunk, sender = super().receive()
        if __debug__:
            self.received_chunks_counter.value += 1
            self.received_bytes_counter.value += len(message)
        return chunk, sender

    def feedback(self):
        old_time = time.time()
        total_sent = 0
        total_received = 0
        sys.stderr.write("\n");
        sys.stderr.write("{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}\n".format("", "", "total", "total", "", ""));
        sys.stderr.write("{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}\n".format("sent", "received", "sent", "received", "sent", "received"));
        sys.stderr.write("{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}\n".format("kbps", "kbps", "kbps", "kbps", "messages", "messages"))
        sys.stderr.write("{}\n".format("="*60))
        sys.stderr.flush()
        while True:
            elapsed_time = time.time() - old_time
            old_time = time.time()
            sent = int(self.sent_bytes_counter.value*8/1000/elapsed_time)
            received = int(self.received_bytes_counter.value*8/1000/elapsed_time)
            total_sent += sent
            total_received += received
            sys.stderr.write(f"{sent:10d}{received:10d}{total_sent:10d}{total_received:10d}{self.sent_messages_counter.value:10d}{self.received_messages_counter.value:10d}\n")
            self.sent_bytes_counter.value = 0
            self.received_bytes_counter.value = 0
            self.sent_messages_counter.value = 0
            self.received_messages_counter.value = 0
            time.sleep(1)

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
