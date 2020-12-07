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
import buffer
import zlib

class Compression (buffer.Buffering):
    def init(self):
        super().__init__()
    
    def pack(self, chunk):
        return zlib.compress(chunk,-1)
    
    def unpack(self, packed_chunk):
        return zlib.decompress(packed_chunk)
    
    def record_send_and_play (self, indata, outdata, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % super().CHUNK_NUMBERS
        packed_chunk = super().pack(self.chunk_number, indata)
        packed_chunk = self.pack(packed_chunk)
        super().send(packed_chunk)
        chunk = super().unbuffer_next_chunk()
        super().play_chunk(outdata, chunk)
    
    def receive_and_buffer(self):
        packed_chunk = super().receive()
        packed_chunk = self.unpack(packed_chunk)
        chunk_number, chunk = super().unpack(packed_chunk)
        self.buffer_chunk(chunk_number, chunk)
        return chunk_number
    
    def run(self):
        print("Press CTRL+c to quit")
        self.played_chunk_number = 0
        with self.stream(self.record_send_and_play):

            first_received_chunk_number = self.receive_and_buffer()

            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer

            while True:
                self.receive_and_buffer()

if __name__ == "__main__":
    try:
        argcomplete.autocomplete(buffer.minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    buffer.minimal.args = buffer.minimal.parser.parse_known_args()[0]
    intercom = Compression()
    intercom.init()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")