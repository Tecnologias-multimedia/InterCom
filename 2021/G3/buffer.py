import sounddevice as sd
import struct
import numpy as np
import time
import minimal
from minimal import *
import math

class Buffer(Minimal):
    CHUNK_NUMBERS = 2**16
    CHUNKS_TO_BUFFER = 8
    tamano = 0
    def init(self, args):
        Minimal.__init__(self)
        self.chunk_time = (args.frames_per_chunk / args.frames_per_second) * 1000
        self.chunks_to_buffer = (int)(math.ceil(args.buffering_time / self.chunk_time))
        print(f"Intercom_buffer: chunks_to_buffer={self.chunks_to_buffer}")
        self.cells_in_buffer = self.chunks_to_buffer * 2
        print(f"Intercom_buffer: cells_in_buffer={self.cells_in_buffer}")
        chunk_number = 0
        self.empty_chunk = self.generate_zero_chunk()

    def receive_and_buffer(self):
        global tamano
        message = super().receive()
        tmp = struct.unpack("I%ds" % tamano, message)
        chunk_number = tmp[0]
        chunk= message[4:]      
        chunk = np.frombuffer(chunk, np.int16).reshape(args.frames_per_chunk, super().NUMBER_OF_CHANNELS)
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number

    def send_chunk(self, chunk):
       
        super().send(chunk)


    def play_chunk(self, DAC):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.empty_chunk
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        DAC[:] = chunk

    def record_send_and_play(self, indata, outdata, frames, time, status):
        global tamano
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.CHUNK_NUMBERS
        tmp = struct.pack("!H", self.recorded_chunk_number) + indata.tobytes()
        b = indata.tobytes()
        tamano = len(b)
        tmp = struct.pack("I%ds" % len(b), self.recorded_chunk_number, b)
        self.send_chunk(tmp)
        self.play_chunk(outdata)


    def run(self):
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.empty_chunk
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        print("Intercom_buffer: press <CTRL> + <c> to quit")
        print("Intercom_buffer: buffering ... ")

        with sd.Stream(samplerate=args.frames_per_second, blocksize=args.frames_per_chunk, dtype=super().SAMPLE_TYPE, channels=super().NUMBER_OF_CHANNELS, callback=self.record_send_and_play):
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    def add_args(self):
        parser = minimal.parser
        parser.add_argument("-b","--buffering_time", type=int, default=500, help="Miliseconds to buffer")
        return parser

if __name__ == "__main__":
    intercom = Buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("Intercom_buffer: goodbye ¯\_(ツ)_/¯")
