#
# Intercom_minimal
# |
# +- Intercom_buffer
#
# Replaces the queue of intercom_minimal by a random access buffer of
# chunks, that allows to extract the chunks from the buffer in the
# playing order, even if the chunks have arrived in a different order.
#
# Buffering implies to spend a buffering time (buffering chunks) that
# increases the delay (the time from when audio is captured by the
# sender and played by the receiver). This time is necessary to hide
# the network jitter. However, the buffer size (and therefore, the
# buffering time) is configurable by the receiver.
#
# The sorting of the chunks at the receiver implies that we must
# transit with each chunk a chunk number to sequence them. We will
# call to this structure a packet.
#

from intercom_minimal import Intercom_minimal

#import array

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

    # Intercom_buffer transmits a chunk number of 16 bits with each
    # chunk of audio. Such number ranges betwen [0, 2**16-1].
    CHUNK_NUMBERS = 2**16

    # Buffer size in chunks. The receiver will wait for receiving at
    # least two chunks whose chunk numbers differs at least in
    # CHUNKS_TO_BUFFER.
    CHUNKS_TO_BUFFER = 8

    def init(self, args):

        # Parse arguments and initialize basic stuff.
        Intercom_minimal.init(self, args)
        self.chunks_to_buffer = args.chunks_to_buffer

        if __debug__:
            print(f"Intercom_buffer: chunks_to_buffer={self.chunks_to_buffer}")

#   +-------+-------+   +-------+
#   | chunk | chunk |...| chunk |
#   +-------+-------+   +-------+
#       0       1   CHUNKS_TO_BUFFER-1
#
# An arriving chunk with chunk_number C is stored at the position
# buffer[C % cells_in_buffer]. This procedure 
#

        

#        with a list of cells (one cell per chunk) in which the arriving chunk (with number) C is stored in the position C % cells_in_buffer. cells_in_buffer = CHUNKS_TO_BUFFER * 2 and therefore, at most only the half of the 
        
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

        # The payload of the UDP packets is a structure with 2 fields:
        #
        #  packet {
        #    uint16 chunk_number;
        #    chunk; /* See Intercom_minimal */
        #  }
        #
        # See:
        # https://docs.python.org/3/library/struct.html#format-characters)
        self.packet_format = f"!H{self.samples_per_chunk}h"

        chunk_number = 0
        a_chunk = Intercom_minimal.generate_zero_chunk()
        self.a_packet = struct.pack(chunk_number, a_chunk)
        #self.socket_buffer = array.array('h', [0] * (2+self.samples_per_chunk*2))
        #self.payload_structure = struct.Struct(f'h{self.samples_per_chunk}P')

        print("Intercom_buffer: buffering ... ")

    # Waits for a new chunk and insert it into the right position of the
    # buffer.
    def receive_and_buffer(self):

        # Receives a chunk. See Intercom_minimal for the structure of a
        # chunk.
        payload = self.receive()
        #print(len(payload))

        # Gives structure to the payload, using the format provided by
        # packet_format (see above): chunk_number is an integer and
        # chunk. See:
        # https://docs.python.org/3/library/struct.html#struct.unpack
        #chunk_number, *chunk = struct.unpack(self.packet_format, payload)
        #chunk_number, chunk = struct.unpack(f"!H{self.samples_per_chunk*2}s", payload)
        #print(type(chunk))
        #chunk = payload[:-1]
        #chunk_number = payload[-1]
        chunk = payload
        #print(len(chunk), chunk_number)

        # Converts the chunk (that at this moment is a bytes object)
        # into a NumPy array. See:
        # https://numpy.org/doc/stable/reference/generated/numpy.asarray.html
        #chunk = np.asarray(chunk)
        #chunk = np.frombuffer(chunk, self.sample_type)

        # Change the structure of the chunk. See Intercom_minimal.
        #chunk = chunk.reshape(self.frames_per_chunk, self.number_of_channels)

        # Inserts the chunk in the buffer.
        #self._buffer[chunk_number % self.cells_in_buffer] = chunk
        #self._buffer[chunk_number % self.cells_in_buffer] = np.asarray(chunk).reshape(self.frames_per_chunk, self.number_of_channels)  # The structure of the chunk is lost during the transit
        #return chunk_number
        return 1
        
    # Now, attached to the chunk (as a header) we need to send the
    # recorded chunk number. Thus, the receiver will know where to
    # insert the chunk into the buffer.
    def send(self, indata):
        #payload = struct.pack(self.packet_format, self.recorded_chunk_number, *(indata.flatten()))
        #self.payload_structure.pack_into(self.socket_buffer, 0, self.recorded_chunk_number, indata)
        #payload = np.append(indata, [self.recorded_chunk_number])
        #print(len(payload))
        #self.sending_sock.sendto(message, (self.destination_address, self.destination_port))
        #Intercom_minimal.send(self, payload)
        Intercom_minimal.send(self, indata)
        self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.CHUNK_NUMBERS

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
        print("Intercom_buffer: press <CTRL> + <c> to quit")
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
