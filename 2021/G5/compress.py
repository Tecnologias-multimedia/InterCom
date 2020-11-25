#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

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
import buffer
import zlib

class Compress(buffer.Buffering):

    def __init__(self):
        ''' Initializes the buffer. '''
        super().__init__()
        if minimal.args.buffering_time <= 0:
            minimal.args.buffering_time = 1 # ms
        print(f"buffering_time = {minimal.args.buffering_time} miliseconds")
        if __debug__:
            print("chunks_to_buffer =", self.chunks_to_buffer)

    def pack(self, chunk_number, chunk):
        chunk = zlib.compress(chunk)
        packed_chunk = struct.pack("!H", chunk_number) + chunk
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        chunk = packed_chunk[2:]
        chunk = zlib.decompress(chunk)
        chunk = np.frombuffer(chunk, dtype=dtype)
        chunk = chunk.reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        return chunk_number, chunk

    def run(self):
        print("Press CTRL+c to quit")
        self.played_chunk_number = 0
        with self.stream(self._record_send_and_play):

            first_received_chunk_number = self.receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer

            while True:
                self.receive_and_buffer()

class Compress__verbose(Compress, buffer.Buffering__verbose):
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
        Compress.send(self, packed_chunk)
        self.sent_bytes_count += len(packed_chunk)
        self.sent_messages_count += 1

    def receive(self):
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
        intercom = Compress__verbose()
    else:
        intercom = Compress()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")