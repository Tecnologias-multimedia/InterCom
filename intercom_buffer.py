#
# Intercom
# |
# +- Intercom_buffer
#
# Adds a (ramdom-access) buffer, which can be used to reorder the
# chunks if they are not transmitted in order by the network.

import sounddevice as sd
import numpy as np
import struct
from intercom import Intercom

if __debug__:
    import sys

class Intercom_buffer(Intercom):

    MAX_CHUNK_NUMBER = 65536
    CHUNKS_TO_BUFFER = 32

    def init(self, args):
        Intercom.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer
        self.cells_in_buffer = self.chunks_to_buffer * 2
        #self._buffer = [self.generate_zero_chunk()] * self.cells_in_buffer
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.generate_zero_chunk()
        self.packet_format = f"!H{self.samples_per_chunk}h"
        if __debug__:
            print(f"chunks_to_buffer={self.chunks_to_buffer}")
        print("buffering")

    # Waits for a new chunk and insert it in the right position of the
    # buffer.
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        chunk_number, *chunk = struct.unpack(self.packet_format, message)
        self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)
        return chunk_number

    # Now, attached to the chunk (as a header) we need to send the
    # recorded chunk number. Thus, the receiver would know where to
    # inser the chunk into the buffer.
    def send(self, indata):
        message = struct.pack(self.packet_format, self.recorded_chunk_number, *(indata.flatten()))
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    def feedback(self):
        sys.stderr.write("."); sys.stderr.flush()

    # Gets the next available chunk from the buffer and send it to the
    # sound device. The played chunks are zeroed in the buffer.
    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk
        if __debug__:
            self.feedback()

    # Almost identical to the parent's one.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        # The recording is performed by sounddevice, which call this
        # method for each recorded chunk.
        self.send(indata)
        self.play(outdata)

    # Runs the intercom and implements the buffer's logic.
    def run(self):
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=self.record_send_and_play):
            print("¯\_(ツ)_/¯ Press <CTRL> + <c> to quit ¯\_(ツ)_/¯")
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    def add_args(self):
        parser = Intercom.add_args(self)
        parser.add_argument("-cb", "--chunks_to_buffer",
                            help="Number of chunks to buffer",
                            type=int, default=Intercom_buffer.CHUNKS_TO_BUFFER)
        return parser

if __name__ == "__main__":
    intercom = Intercom_buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
