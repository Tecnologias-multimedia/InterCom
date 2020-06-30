#
# Intercom_minimal
# |
# +- Intercom_buffer
#
# Replaces the queue of intercom_minimal by a random access buffer of
# chunks, that allows to extract the chunks from the buffer in the
# correct (playing) order, even if the chunks have arrived in a
# different order.
#
# Buffering implies to spend a buffering time (buffering chunks) that
# increases the delay (the time from when a sample of audio is
# captured by the sender and played by the receiver). This time is
# necessary to hide the network jitter, when it exists. However, the
# buffer size (and therefore, the buffering time) is configurable by
# the receiver (it can be as smaller as only 1 chunk).
#
# The sorting of the chunks at the receiver implies that we must
# transit, with each chunk of audio, a chunk number to sequence
# them. We will call to this structure "packet".
#

from intercom_minimal import Intercom_minimal

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

    # Accumulated percentage of used CPU. 
    CPU_total = 0

    # Number of samples of the CPU usage.
    CPU_samples = 0

    # CPU usage average.
    CPU_average = 0

class Intercom_buffer(Intercom_minimal):

    # Intercom_buffer transmits a chunk number of 16 bits with each
    # chunk of audio. Such number ranges betwen [0, 2**15-1] (int16).
    CHUNK_NUMBERS = 2**15

    # Default buffer size in chunks. The receiver will wait for
    # receiving at least two chunks whose chunk numbers differs at
    # least in CHUNKS_TO_BUFFER.
    CHUNKS_TO_BUFFER = 8

    def init(self, args):

        # Parse arguments and initialize basic stuff.
        Intercom_minimal.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer

        if __debug__:
            print(f"Intercom_buffer: chunks_to_buffer={self.chunks_to_buffer}")
        
        # By definition, the buffer has CHUNKS_TO_BUFFER chunks when
        # it is full (and logically, the buffer is empty if there is
        # no chunks inside). However, in order to accommodate large
        # jitters, the buffer is built using a list of
        # 2*CHUNKS_TO_BUFFER empty chunks. Thus, in an ideal
        # situation, half of the list will contain chunks that has
        # been received but that has not been played, and the other
        # half will contain old chunks (that has been played
        # recently). Notice that the buffering time is the time that
        # is needed for fill in half of the buffer (not necessarily
        # starting at cell 0).

        # The buffer is implemented as an sliding window of size
        # CHUNKS_TO_BUFFER that moves ciclically over
        # CHUNKS_TO_BUFFER*2 cells. Thus, in an ideal scenario, half
        # of the cells of the buffer will contain unplayed chunks and
        # the other half, already played chunks.
        self.cells_in_buffer = self.chunks_to_buffer * 2

        # See:
        # https://docs.python.org/3/library/struct.html#format-characters)
        self.packet_format = f"hh{self.samples_per_chunk}h" # Ojo, quitar self cuando sea posible

        # self.chunk is an structure with audio and a chunk counter:
        #
        #  chunk {
        #    uint16 chunk_number;
        #    [frames_per_chunk][number_of_channels] int16 sample;
        #  }
        
        chunk_number = 0
        self.empty_chunk = self.generate_zero_chunk()
        self.chunk = np.concatenate(([[0, 0]], self.empty_chunk)).astype(np.int16)

        # Running the user pacifier.
        p = Process(target=self.feedback)
        p.start()

    # Waits for a new chunk and insert it into the right position of
    # the buffer. As the receive_and_queue() method in
    # Intercom_minimal, this method is called from an infinite loop.
    def receive_and_buffer(self):

        # Receives a chunk in self.chunk.
        self.receive()
        chunk_number = self.chunk[0, 0]
        audio_chunk = self.chunk[1:,:]
        self._buffer[chunk_number % self.cells_in_buffer] = audio_chunk
        return chunk_number
        
    # Now, attached to the chunk (as a header) we need to send the
    # recorded chunk number. Thus, the receiver will know where to
    # insert the chunk into the buffer.
    def send(self, data):
        self.chunk[0, 0] = self.recorded_chunk_number
        self.chunk[1:,:] = data[:,:]
        Intercom_minimal.send(self, self.chunk)

    # Gets the next available chunk from the buffer and send it to the
    # sound device. The played chunks are zeroed in the buffer.
    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.empty_chunk
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk

    # Almost identical to Intercom_minimal.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        # The recording is performed by sounddevice, which call this
        # method for each recorded chunk.
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.CHUNK_NUMBERS
        self.send(indata)
        self.play(outdata)

    # Runs the intercom and implements the buffer's logic.
    def run(self):
        
        # Buffer construction.
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.empty_chunk #self.generate_zero_chunk()

        # Chunks counters.
        self.recorded_chunk_number = 0
        self.played_chunk_number = 0

        print("Intercom_buffer: press <CTRL> + <c> to quit")
        print("Intercom_buffer: buffering ... ")

        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=self.sample_type, channels=self.number_of_channels, callback=self.record_send_and_play):
            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()

    # Shows CPU usage.
    def print_feedback_message(self):
        global CPU_total  # Be careful, variables updated only in the subprocess
        global CPU_samples
        global CPU_average
        CPU_usage = psutil.cpu_percent()
        CPU_total += CPU_usage
        CPU_samples += 1
        CPU_average = CPU_total/CPU_samples
        print(f"{int(CPU_usage)}/{int(CPU_average)}", flush=True, end=' ')

    # This method runs in a different process to the intercom, and its
    # only task is to print the feedback messages with the CPU load,
    # waiting for the interrupt of the user (CTRL+C).
    def feedback(self):
        global CPU_average
        try:
            while True:
                self.print_feedback_message()
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nIntercom_buffer: average CPU usage = {CPU_average} %")

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
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("Intercom_buffer: goodbye ¯\_(ツ)_/¯")
