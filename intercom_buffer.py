# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom import Intercom

if __debug__:
    import sys

class Intercom_buffer(Intercom):

    MAX_CHUNK_NUMBER = 65536

    def init(self, args):
        Intercom.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer
        self.cells_in_buffer = self.chunks_to_buffer * 2
        self._buffer = [self.generate_zero_chunk()] * self.cells_in_buffer
        self.packet_format = f"!H{self.samples_per_chunk}h"
        if __debug__:
            print(f"chunks_to_buffer={self.chunks_to_buffer}")

    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        chunk_number, *chunk = struct.unpack(self.packet_format, message)
        self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)
        return chunk_number

    def record_and_send(self, indata):
        ##signs = indata >> 15
        #signs = indata & 0x8000
        #magnitudes = abs(indata)
        ##indata = (signs << 15) | magnitudes
        #indata = (signs | magnitudes).astype(np.int16)
        message = struct.pack(self.packet_format, self.recorded_chunk_number, *(indata.flatten()))
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))

    def feedback(self):
        sys.stderr.write("."); sys.stderr.flush()

    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        #signs = chunk >> 15
        ##signs = (chunk & 0x8000).astype(np.int16)
        #magnitudes = chunk & 0x7FFF
        #chunk = magnitudes + magnitudes*signs*2
        ##chunk = ((~signs & magnitudes) | ((-magnitudes) & signs)).astype(np.int16)
        #print(chunk)
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        print(chunk)
        outdata[:] = chunk
        if __debug__:
            self.feedback()

    def record_send_and_play(self, indata, outdata, frames, time, status):    
        # record
        self.record_and_send(indata)
        self.play(outdata)

    def run(self):
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=self.record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    def add_args(self):
        parser = Intercom.add_args(self)
        parser.add_argument("-cb", "--chunks_to_buffer", help="Number of chunks to buffer", type=int, default=32)
        return parser

if __name__ == "__main__":
    intercom = Intercom_buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
