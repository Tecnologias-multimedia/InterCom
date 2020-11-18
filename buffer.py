# Adding a buffer.
#
# The buffer allows to reorder the chunks if they are not transmitted
# in order by the network.
import sounddevice as sd                                                        # https://python-sounddevice.readthedocs.io
import numpy as np                                                              # https://numpy.org/
import argparse                                                                 # https://docs.python.org/3/library/argparse.html
import socket                                                                   # https://docs.python.org/3/library/socket.html
import queue
import struct
from minimal import Minimal

if __debug__:
    import sys

class Buffer(Minimal):

    MAX_CHUNK_NUMBER = 65536

    def init(self, args):
        ####
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", args.listening_port)
        self.sock.bind(self.listening_endpoint)
        self.chunk_time = args.frames_per_chunk / args.frames_per_second
        self.zero_chunk = self.generate_zero_chunk()
        ####

        self.samples_per_chunk = args.frames_per_chunk * Minimal.NUMBER_OF_CHANNELS
        self.chunks_to_buffer = args.chunks_to_buffer
        self.cells_in_buffer = self.chunks_to_buffer * 2
        #self._buffer = [self.generate_zero_chunk()] * self.cells_in_buffer
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.generate_zero_chunk()

        self.packet_format = f"!H{self.samples_per_chunk}h"
        if __debug__:
            print(f"chunks_to_buffer={self.chunks_to_buffer}")

    def generate_zero_chunk(self):
        return np.zeros((args.frames_per_chunk, Minimal.NUMBER_OF_CHANNELS), Minimal.SAMPLE_TYPE)


    def receive_and_buffer(self):
        message, source_address = self.sock.recvfrom(Minimal.MAX_PAYLOAD_BYTES)
        chunk_number, *chunk = struct.unpack(self.packet_format, message)
        self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(args.frames_per_chunk, Minimal.NUMBER_OF_CHANNELS)
        return chunk_number

    def send(self, indata):
        message = struct.pack(self.packet_format, self.recorded_chunk_number, *(indata.flatten()))
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        self.sock.sendto(message, (args.destination_address, args.destination_port))

    def feedback(self):
        sys.stderr.write("."); sys.stderr.flush()

    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk
        if __debug__:
            self.feedback()

    def record_send_and_play(self, indata, outdata, frames, time, status):    # The recording is performed by sounddevice
        self.send(indata)
        self.play(outdata)

    def run(self):
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        with sd.Stream(samplerate=args.frames_per_second, blocksize=args.frames_per_chunk, dtype=np.int16, channels=Minimal.NUMBER_OF_CHANNELS, callback=self.record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    def int_or_str(self,text):
        try:
            return int(text)
        except ValueError:
            return text
    def add_args(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-i", "--input-device", type=self.int_or_str, help="Input device ID or substring")
        parser.add_argument("-o", "--output-device", type=self.int_or_str, help="Output device ID or substring")
        parser.add_argument("-s", "--frames_per_second", type=float, default=44100, help="sampling rate in frames/second")
        parser.add_argument("-c", "--frames_per_chunk", type=int, default=1024, help="Number of frames in a chunk")
        parser.add_argument("-l", "--listening_port", type=int, default=4444, help="My listening port")
        parser.add_argument("-a", "--destination_address", type=self.int_or_str, default="localhost", help="Destination (interlocutor's listening-) address")
        parser.add_argument("-p", "--destination_port", type=int, default=4444, help="Destination (interlocutor's listing-) port")
        parser.add_argument("-cb", "--chunks_to_buffer", help="Number of chunks to buffer", type=int, default=32)
        return parser

if __name__ == "__main__":
    intercom = Buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
