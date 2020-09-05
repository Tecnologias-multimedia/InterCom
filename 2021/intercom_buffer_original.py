#
# Intercom
# |
# +- Intercom_buffer
#
# Adds a (ramdom-access) buffer, which can be used to reorder the
# chunks if they are not transmitted in order by the network.


from intercom_minimal import Intercom_minimal

import array

try:
    import sounddevice as sd
except ModuleNotFoundError:
    import os
    os.system("pip3 install sounddevice --user")
    import sounddevice as sd

try:
    import numpy as np
except ModuleNotFoundError:
    print("Installing numpy with pip")
    import os
    os.system("pip3 install numpy --user")
    import numpy as np

import struct

if __debug__:
    import sys

    try:
        import psutil
    except ModuleNotFoundError:
        import os
        os.system("pip3 install psutil --user")
        import psutil
    
    import time
    from multiprocessing import Process

    CPU_total = 0
    CPU_samples = 0
    CPU_average = 0

class Intercom_buffer(Intercom_minimal):

    MAX_CHUNK_NUMBER = 65536
    CHUNKS_TO_BUFFER = 8

    def init(self, args):
        Intercom_minimal.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer
        self.cells_in_buffer = self.chunks_to_buffer * 2
        #self._buffer = [self.generate_zero_chunk()] * self.cells_in_buffer
        self.packet_format = f"hh{self.samples_per_chunk}h"
        self.sample_type = np.int16
        if __debug__:
            print(f"intercom_buffer: chunks_to_buffer={self.chunks_to_buffer}")
        print("intercom_buffer: buffering")
        chunk_number = 0
        self.empty_chunk = self.generate_zero_chunk()
        print("type=", type(self.empty_chunk[0,0]))
        self.chunk = np.concatenate(([[0, 0]], self.empty_chunk)).astype(np.int16)
        print("type=", type(self.chunk[0,0]))

    # Waits for a new chunk and insert it in the right position of the
    # buffer.
    def receive_and_buffer(self):
        self.receive()
        chunk_number = self.chunk[0, 0]
        chunk = self.chunk[1:,:]
        #print(chunk.shape)
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number
    def _receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom_minimal.MAX_PAYLOAD_BYTES)
        chunk = np.frombuffer(message, np.int16)
        ###print(len(chunk))
        chunk_all = chunk.reshape((self.frames_per_chunk+1), self.number_of_channels)
        chunk_number = chunk_all[0, 0]
        print(id(message), id(chunk), id(chunk_all))
        print(chunk_number)
        chunk = chunk_all[1:,:]
        #print(chunk.shape)
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number
    def _receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom_minimal.MAX_PAYLOAD_BYTES)
        chunk_number, _, *chunk = struct.unpack(self.packet_format, message)
        chunk = np.asarray(chunk)
        print(len(chunk))
        chunk = chunk.reshape(self.frames_per_chunk, self.number_of_channels)
        #print(chunk.shape)
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number

    # Now, attached to the chunk (as a header) we need to send the
    # recorded chunk number. Thus, the receiver would know where to
    # inser the chunk into the buffer.
    def send(self, indata):
        message = struct.pack(self.packet_format, self.recorded_chunk_number, self.recorded_chunk_number, *(indata.flatten()))
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    # Gets the next available chunk from the buffer and send it to the
    # sound device. The played chunks are zeroed in the buffer.
    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk
#        if __debug__:
#            self.feedback()

    # Almost identical to the parent's one.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        # The recording is performed by sounddevice, which call this
        # method for each recorded chunk.
        self.send(indata)
        self.play(outdata)

    # Runs the intercom and implements the buffer's logic.
    def run(self):
        print("intercom_buffer: ¯\_(ツ)_/¯ Press <CTRL> + <c> to quit ¯\_(ツ)_/¯")
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.generate_zero_chunk()
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        p = Process(target=self.feedback)
        p.start()
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=self.sample_type, channels=self.number_of_channels, callback=self.record_send_and_play):
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    def feedback(self):
        while True:
            sys.stderr.write("."); sys.stderr.flush()
            time.sleep(1)

    def add_args(self):
        parser = Intercom_minimal.add_args(self)
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
