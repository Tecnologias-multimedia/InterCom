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
