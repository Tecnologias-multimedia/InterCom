#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""Over minimal, implements a random access buffer structure for hiding the jitter."""

import argparse
import sounddevice as sd
import numpy as np
import socket
import time
import psutil
import math
import struct
import threading
import minimal
import soundfile as sf
import logging

minimal.parser.add_argument("-b", "--buffering_time", type=int, default=150, help="Miliseconds to buffer")

class Buffering(minimal.Minimal):

    CHUNK_NUMBERS = 1 << 15 # Enought for most buffering times.

    def __init__(self):
        ''' Initializes the buffer. '''
        super().__init__()
        logging.info(__doc__)
        if minimal.args.buffering_time <= 0:
            minimal.args.buffering_time = 1 # ms
        logging.info(f"buffering_time = {minimal.args.buffering_time} miliseconds")
        self.chunks_to_buffer = int(math.ceil(minimal.args.buffering_time / 1000 / self.chunk_time))
        self.zero_chunk = self.generate_zero_chunk()
        self.cells_in_buffer = self.chunks_to_buffer * 2
        self._buffer = [None] * self.cells_in_buffer
        for i in range(self.cells_in_buffer):
            self._buffer[i] = self.zero_chunk
        #self.sock.settimeout(self.chunk_time)
        #self.sock.settimeout(0)
        self.chunk_number = 0
        logging.info(f"chunks_to_buffer = {self.chunks_to_buffer}")

        if minimal.args.filename:
            logging.info(f"Using \"{minimal.args.filename}\" as input")
            self.wavfile = sf.SoundFile(minimal.args.filename, 'r')
            self._handler = self._read_IO_and_play
            self.stream = self.file_stream
        else:
            self._handler = self._record_IO_and_play
            self.stream = self.mic_stream

    def pack(self, chunk_number, chunk):
        '''Concatenates a chunk number to the chunk.'''
        packed_chunk = struct.pack("!H", chunk_number) + chunk.tobytes()
        return packed_chunk

    def unpack(self, packed_chunk):
        '''Splits the packed chunk into a chunk number and a chunk.'''
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        chunk = packed_chunk[2:]
        # Notice that struct.calcsize('H') = 2
        chunk = np.frombuffer(chunk, dtype=np.int16)
        #chunk = chunk.reshape(minimal.args.frames_per_chunk, minimal.args.number_of_channels)
        return chunk_number, chunk

    def buffer_chunk(self, chunk_number, chunk):
        self._buffer[chunk_number % self.cells_in_buffer] = chunk

    def unbuffer_next_chunk(self):
        chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
        return chunk

    def play_chunk(self, DAC, chunk):
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        chunk = chunk.reshape(minimal.args.frames_per_chunk, minimal.args.number_of_channels)
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

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        packed_chunk = self.pack(self.chunk_number, ADC)
        self.send(packed_chunk)
        chunk = self.unbuffer_next_chunk()
        self.play_chunk(DAC, chunk)

    def _read_IO_and_play(self, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        read_chunk = self.read_chunk_from_file()
        packed_chunk = self.pack(self.chunk_number, read_chunk)
        self.send(packed_chunk)
        chunk = self.unbuffer_next_chunk()
        self.play_chunk(DAC, chunk)
        return read_chunk

    def run(self):
        '''Creates the stream, install the callback function, and waits for
        an enter-key pressing.'''
        logging.info("Press CTRL+c to quit")
        self.played_chunk_number = 0
        with self.stream(self._handler):
            first_received_chunk_number = self.receive_and_buffer()
            logging.debug("first_received_chunk_number =", first_received_chunk_number)

            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            # The previous selects the first chunk to be played the
            # one (probably empty) that are in the buffer
            # <self.chunks_to_buffer> position before
                # <first_received_chunk_number>.

            while True:# and not self.input_exhausted:
                self.receive_and_buffer()

class Buffering__verbose(Buffering, minimal.Minimal__verbose):
    
    def __init__(self):
        super().__init__()
        #self.args = args
        #Buffering.__init__(self)
        #Minimal__verbose.__init__(self, args)

    def send(self, packed_chunk):
        '''Computes the number of sent bytes and the number of sent
        packets.'''
        Buffering.send(self, packed_chunk)
        self.sent_bytes_count += len(packed_chunk)
        self.sent_messages_count += 1

    def receive(self):
        '''Computes the number of received bytes and the number of received
        packets.'''
        packed_chunk = Buffering.receive(self)
        self.received_bytes_count += len(packed_chunk)
        self.received_messages_count += 1
        return packed_chunk

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        if minimal.args.show_samples:
            self.show_recorded_chunk(ADC)

        super()._record_IO_and_play(ADC, DAC, frames, time, status)

        if minimal.args.show_samples:
            self.show_played_chunk(DAC)

        self.recorded_chunk = DAC
        self.played_chunk = ADC
        #self.recorded_chunk[512:,:]=20000 # <--------------------------------------------

    def _read_IO_and_play(self, DAC, frames, time, status):
        read_chunk = super()._read_IO_and_play(DAC, frames, time, status)

        if minimal.args.show_samples:
            self.show_recorded_chunk(read_chunk)
            self.show_played_chunk(DAC)

        self.recorded_chunk = DAC

        return read_chunk

    def loop_receive_and_buffer(self):
        first_received_chunk_number = self.receive_and_buffer()
        if __debug__:
            print("first_received_chunk_number =", first_received_chunk_number)
        self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
        if minimal.args.show_spectrum:
            while self.total_number_of_sent_chunks < self.chunks_to_sent:# and not self.input_exhausted:
                self.receive_and_buffer()
                self.update_display() # PyGame cannot run in a thread :-/
        else:
            while self.total_number_of_sent_chunks < self.chunks_to_sent:# and not self.input_exhausted:
                self.receive_and_buffer()

    def run(self):
        cycle_feedback_thread = threading.Thread(target=self.loop_cycle_feedback)
        cycle_feedback_thread.daemon = True        
        self.print_running_info()
        super().print_header()
        self.played_chunk_number = 0
        with self.stream(self._handler):
            cycle_feedback_thread.start()
            self.loop_receive_and_buffer()

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    minimal.parser.description = __doc__

    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")

    minimal.args = minimal.parser.parse_known_args()[0]
    
    if minimal.args.list_devices:
        print("Available devices:")
        print(sd.query_devices())
        quit()

    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        #intercom = Buffering__verbose(minimal.args)
        intercom = Buffering__verbose()
    else:
        intercom = Buffering()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
