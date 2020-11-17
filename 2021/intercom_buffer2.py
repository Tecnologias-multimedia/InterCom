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

# To-do:
#
# 1. Implement the treatment of mono signals.
# 2. Compute (and show) the buffering time.

from intercom_minimal2 import Intercom_minimal
import sounddevice as sd
import numpy as np
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

    # Intercom_buffer transmits chunk number (a signed integer of 16
    # bits (int16) with each chunk of audio. Such number ranges betwen
    # [-2^15, 2**15-1] (values that an int16 can take), although only
    # natural (non negative) values have been considered for
    # sequencing chunks. Therefore, are only 2**15 different chunk
    # numbers are possible.
    CHUNK_NUMBERS = 2**15

    # Default buffer size in chunks. The receiver will wait for
    # receiving at least two chunks whose chunk numbers differs at
    # least in CHUNKS_TO_BUFFER.
    CHUNKS_TO_BUFFER = 8

    def init(self, args):
        Intercom_minimal.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer
        print(f"Intercom_buffer: chunks_to_buffer={self.chunks_to_buffer}")
        
        # By definition, the buffer has CHUNKS_TO_BUFFER chunks when
        # it is full (and logically, the buffer is empty if there is
        # no chunks inside). However, in order to accommodate large
        # jitters, the buffer is implemented as an sliding window of
        # size CHUNKS_TO_BUFFER that moves ciclically over
        # CHUNKS_TO_BUFFER*2 cells. Thus, in an ideal situation (if
        # all the chunks have been received in order), half of the
        # cells of the complete structure will contain chunks that has
        # been received but that has not been played, and the other
        # half will contain empty chunks (the chunks are zeroed after
        # they has been played). Notice that the buffering time is the
        # time that is needed for fill in half of the buffer (not
        # necessarily starting at cell 0).
        self.cells_in_buffer = self.chunks_to_buffer * 2
        print(f"Intercom_buffer: cells_in_buffer={self.cells_in_buffer}")

        # Now, a chunk is an structure with audio and a chunk
        # counter:
        #
        #  chunk {
        #    int16 chunk_number, unused;
        #    int16 [frames_per_chunk][number_of_channels] sample;
        #  }
        #
        # self.chunk is used for giving format to the incomming
        # chunks.
        #self.chunk_buffer = np.concatenate(([[0, 0]], self.generate_zero_chunk())).astype(np.int16)
        
        chunk_number = 0

        # Initially, all the cells of the buffer will point to this
        # empty chunk.
        self.empty_chunk = self.generate_zero_chunk()

        # Running the user pacifier.
        p = Process(target=self.feedback)
        p.start()

    # Waits for a new chunk and insert it into the right position of
    # the buffer. As the receive_and_queue() method in
    # Intercom_minimal, this method is called from an infinite loop.
    def receive_and_buffer(self):
        message = self.receive()
        tmp = np.frombuffer(message, dtype=np.int16).reshape(self.frames_per_chunk+1, self.number_of_channels)
        chunk_number = tmp[0, 0]
        chunk = tmp[1:,:]
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number
    def _receive_and_buffer(self): # This methos should be a bit
                                   # faster than the previous one,
                                   # although it does not work
                                   # properly :-/ (probably,
                                   # "self.chunk_buffer" is
                                   # overwritten by the OS before we
                                   # play the chunks and notice that
                                   # the buffer does not store the
                                   # chunks of audio, but the pointers
                                   # to the chunks of audio).
        recv_bytes, sender = self.receiving_sock.recvfrom_into(self.chunk_buffer)
        chunk_number = self.chunk_buffer[0, 0]
        chunk = self.chunk_buffer[1:,:]
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number

    # Sends a chunk.
    def send(self, chunk):
        # Now, attached to the chunk (as a header) we need to send the
        # recorded chunk number. Thus, the receiver will know where to
        # insert the chunk into the buffer.
        chunk = np.concatenate(([[self.recorded_chunk_number, 0]], chunk)).astype(np.int16)
        super().send(chunk)

    # Gets the next available chunk from the buffer and send it to the
    # sound device. The played chunks are zeroed in the buffer.
    def play(self, outdata):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.empty_chunk
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        outdata[:] = chunk

    # Almost identical to the method record_send_and_play() of
    # Intercom_minimal, except that the recorded_chunk_number is
    # computed (remember that sounddevice calls this method for each
    # recorded chunk).
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.CHUNK_NUMBERS
        self.send(indata)
        self.play(outdata)

    # Runs the intercom and implements the buffer's logic.
    def run(self):
        
        # Buffer creation.
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.empty_chunk

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
        # Be careful, variables updated only in the subprocess.
        global CPU_total
        global CPU_samples
        global CPU_average
        CPU_usage = psutil.cpu_percent()
        CPU_total += CPU_usage
        CPU_samples += 1
        CPU_average = CPU_total/CPU_samples
        print(f"{int(CPU_usage)}/{int(CPU_average)}", flush=True, end=' ')

    # This method runs in a different process to the intercom, and its
    # only task is to print the feedback messages with the CPU load,
    # waiting for the interrupt signal generated by the user (CTRL+C).
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
