#
# Intercom_minimal
# |
# +- Intercom_buffer
#
# Replaces the queue of intercom_minimal by a (ramdom-access) buffer,
# which can be used to reorder the chunks if they are not transmitted
# in order by the network. The buffer structure gives more control
# than a queue.

from intercom_minimal import Intercom_minimal
try:
    import numpy as np  # https://numpy.org
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

class Intercom_buffer(Intercom_minimal):

    MAX_CHUNK_NUMBER = 65536
    CHUNKS_TO_BUFFER = 8

    def init(self, args):
        Intercom_minimal.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer
        self.cells_in_buffer = self.chunks_to_buffer * 2
        #self._buffer = [self.generate_zero_chunk()] * self.cells_in_buffer
        self.packet_format = f"!H{self.samples_per_chunk}h"
        self.precision_type = np.int16
        if __debug__:
            print(f"Intercom_buffer: chunks_to_buffer={self.chunks_to_buffer}")
        print("Intercom_buffer: buffering")

    # Waits for a new chunk and insert it into the right position of the
    # buffer.
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom_minimal.MAX_MESSAGE_BYTES)
        # stereo_payload {
        #   int32 chunk_number;
        #   stereo_frame[frames_per_chunk];
        # }
        # stereo_frame {
        #   int16 left_sample, right_sample;
        # }
        # mono_payload {
        #   int32 chunk_number;
        #   mono_frame[frames_per_chunk];
        # }
        # mono_frame {
        #   int16 sample;
        # }
        chunk_number, *chunk = struct.unpack(self.packet_format, message)
        self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)  # The structure of the chunk is lost during the transit
        return chunk_number

    # Now, attached to the chunk (as a header) we need to send the
    # recorded chunk number. Thus, the receiver will know where to
    # insert the chunk into the buffer.
    def send(self, indata):
        message = struct.pack(self.packet_format, self.recorded_chunk_number, *(indata.flatten()))
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    # Gets the next available chunk from the buffer and send it to the
    # sound device. The played chunks are zeroed in the buffer.
    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk

    # Almost identical to the parent's one.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        # The recording is performed by sounddevice, which call this
        # method for each recorded chunk.
        self.send(indata)
        self.play(outdata)

    # Runs the intercom and implements the buffer's logic.
    def run(self):
        import sounddevice as sd
        import numpy as np
        import struct
        if __debug__:
            import sys
            import time
            from multiprocessing import Process
        print("intercom_buffer: ¯\_(ツ)_/¯ Press <CTRL> + <c> to quit ¯\_(ツ)_/¯")
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.generate_zero_chunk()
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        p = Process(target=self.feedback)
        p.start()
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=self.precision_type, channels=self.number_of_channels, callback=self.record_send_and_play):
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    def feedback(self):
        while True:
            self.feedback_message()
            time.sleep(1)

    def add_args(self):
        parser = Intercom_minimal.add_args(self)
        parser.add_argument("-b", "--chunks_to_buffer",
                            help="Number of chunks to buffer",
                            type=int, default=Intercom_buffer.CHUNKS_TO_BUFFER)
        return parser

if __name__ == "__main__":
    intercom = Intercom_buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
