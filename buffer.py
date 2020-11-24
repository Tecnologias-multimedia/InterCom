<<<<<<< HEAD
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

import sounddevice as sd
import numpy as np
import psutil
import time
from multiprocessing import Process
#importamos struct y heredamos minimal
import struct
import minimal
from minimal import *
        
# Accumulated percentage of used CPU. 
CPU_total = 0

# Number of samples of the CPU usage.
CPU_samples = 0

# CPU usage average.
CPU_average = 0

class Buffer(Minimal):

    # Intercom_buffer transmits chunk number (a unsigned integer of 16
    # bits (int16) with each chunk of audio
    CHUNK_NUMBERS = 2**16

    # Default buffer size in chunks. The receiver will wait for
    # receiving at least two chunks whose chunk numbers differs at
    # least in CHUNKS_TO_BUFFER.
    CHUNKS_TO_BUFFER = 8

    def init(self, args):
        Minimal.__init__(self)
        chunk_time = args.frames_per_chunk / args.frames_per_second
        self.chunks_to_buffer = (int)(args.buffering_time / (chunk_time*1000))
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

        message = super().receive()
        tmp = struct.unpack("=I%sf"%(args.frames_per_chunk*super().NUMBER_OF_CHANNELS), message)
        chunk_number = tmp[0]
        chunk = np.reshape(tmp[1:], (args.frames_per_chunk, super().NUMBER_OF_CHANNELS))
        self._buffer[chunk_number % self.cells_in_buffer] = chunk
        return chunk_number

    # Sends a chunk.
    def send(self, chunk):
        # Now, attached to the chunk (as a header) we need to send the
        # recorded chunk number. Thus, the receiver will know where to
        # insert the chunk into the buffer.
        chunk = struct.pack("=I%sf"%(args.frames_per_chunk*super().NUMBER_OF_CHANNELS), self.recorded_chunk_number, *chunk.flatten('F'))
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

        with sd.Stream(samplerate=args.frames_per_second, blocksize=args.frames_per_chunk, dtype=super().SAMPLE_TYPE, channels=super().NUMBER_OF_CHANNELS, callback=self.record_send_and_play):
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
        #parser = Intercom_minimal.add_args(self)
        #parser.add_argument("-b", "--chunks_to_buffer",
        #                    help="Number of chunks to buffer",
        #                    type=int, default=Intercom_buffer.CHUNKS_TO_BUFFER)
        #return parser
        minimal.parser.add_argument("-b","--buffering_time", type=int, default=500, help="Milisegundos")
        return minimal.parser

if __name__ == "__main__":
    intercom = Buffer()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("Intercom_buffer: goodbye ¯\_(ツ)_/¯")
=======
#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (with buffering). '''

import argparse
import sounddevice as sd
import numpy as np
import socket
import time
import psutil
import math
import struct
import threading
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal

minimal.parser.add_argument("-b", "--buffering_time", type=int, default=100, help="Miliseconds to buffer")

class Buffering(minimal.Minimal):

    CHUNK_NUMBERS = 1 << 15 # Enought for most buffering times.
    
    """
    Implements a random access buffer structure for hiding the jitter.

    Class attributes
    ----------------

    Methods
    -------
    __init__()
    pack(chunk)
    send(packed_chunk)
    receive()
    unpack(packed_chunk)
    generate_zero_chunk()
    _record_io_and_play()
    stream()
    run()
    """

    def __init__(self):
        ''' Initializes the buffer. '''
        super().__init__()
        if minimal.args.buffering_time <= 0:
            minimal.args.buffering_time = 1 # ms
        print(f"buffering_time = {minimal.args.buffering_time} miliseconds")
        self.chunks_to_buffer = int(math.ceil(minimal.args.buffering_time / 1000 / self.chunk_time))
        self.zero_chunk = self.generate_zero_chunk()
        self.cells_in_buffer = self.chunks_to_buffer * 2
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.zero_chunk
        self.chunk_number = 0
        if __debug__:
            print("chunks_to_buffer =", self.chunks_to_buffer)

    def pack(self, chunk_number, chunk):
        ''' Concatenates a chunk number to the chunk.

        Parameters
        ----------
        chunk : numpy.ndarray
            A chunk of audio.

        Returns
        -------
        bytes
            A packed chunk.

        '''
        packed_chunk = struct.pack("!H", chunk_number) + chunk.tobytes()
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        ''' Splits the packed chunk into a chunk number and a chunk.

        Parameters
        ----------

        packed_chunk : bytes

            A packet.

        Returns
        -------

        chunk_number : int
        chunk : numpy.ndarray

            A chunk (a pointer to the socket's read-only buffer).
        '''
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        chunk = packed_chunk[2:]
        # Notice that struct.calcsize('H') = 2
        chunk = np.frombuffer(chunk, dtype=dtype)
        chunk = chunk.reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        return chunk_number, chunk

    def buffer_chunk(self, chunk_number, chunk):
        self._buffer[chunk_number % self.cells_in_buffer] = chunk

    def unbuffer_next_chunk(self):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        return chunk

    def play_chunk(self, DAC, chunk):
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        DAC[:] = chunk

    def receive(self):
        packed_chunk, sender = self.sock.recvfrom(self.MAX_PAYLOAD_BYTES)
        return packed_chunk

    def receive_and_buffer(self):
        if __debug__:
            print(next(minimal.spinner), end='\b', flush=True)
        packed_chunk = self.receive()
        chunk_number, chunk = self.unpack(packed_chunk)
        self.buffer_chunk(chunk_number, chunk)
        return chunk_number
        
    def _record_send_and_play(self, indata, outdata, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        packed_chunk = self.pack(self.chunk_number, indata)
        self.send(packed_chunk)
        chunk = self.unbuffer_next_chunk()
        self.play_chunk(outdata, chunk)

    def run(self):
        '''Creates the stream, install the callback function, and waits for
        an enter-key pressing.'''
        print("Press CTRL+c to quit")
        self.played_chunk_number = 0
        with self.stream(self._record_send_and_play):

            first_received_chunk_number = self.receive_and_buffer()
            if __debug__:
                print("first_received_chunk_number =", first_received_chunk_number)

            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            # The previous selects the first chunk to be played the
            # one (probably emptty) that are in the buffer
            # self.chunks_to_buffer position before
            # first_received_chunk_number.

            while True:
                self.receive_and_buffer()

class Buffering__verbose(Buffering, minimal.Minimal__verbose):
    ''' Verbose version of Buffering.

    Methods
    -------
    __init__()
    send(packed_chunk)
    receive()
    cycle_feedback()
    run()
    '''

    def __init__(self):
        super().__init__()
        thread = threading.Thread(target=self.feedback)
        thread.daemon = True # To obey CTRL+C interruption.
        thread.start()

    def feedback(self):
        while True:
            time.sleep(self.SECONDS_PER_CYCLE)
            self.cycle_feedback()

    def send(self, packed_chunk):
        ''' Computes the number of sent bytes and the number of sent packets. '''
        Buffering.send(self, packed_chunk)
        self.sent_bytes_count += len(packed_chunk)
        self.sent_messages_count += 1

    def receive(self):
        ''' Computes the number of received bytes and the number of received packets. '''
        packed_chunk = super().receive()
        self.received_bytes_count += len(packed_chunk)
        self.received_messages_count += 1
        return packed_chunk

    def _record_send_and_play(self, indata, outdata, frames, time, status):
        if minimal.args.show_samples:
            self.show_indata(indata)

        super()._record_send_and_play(indata, outdata, frames, time, status)

        if minimal.args.show_samples:
            self.show_outdata(outdata)

    def run(self):
        '''.'''
        print("Press CTRL+c to quit")
        self.print_header()
        try:
            self.played_chunk_number = 0
            with self.stream(self._record_send_and_play):
                first_received_chunk_number = self.receive_and_buffer()
                if __debug__:
                    print("first_received_chunk_number =", first_received_chunk_number)
                self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
                while True:
                    self.receive_and_buffer()
        except KeyboardInterrupt:
            self.print_final_averages()

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Buffering__verbose()
    else:
        intercom = Buffering()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
>>>>>>> 975ad4b0e61a0c5da68ebee32e8fb4f619adbbfc
