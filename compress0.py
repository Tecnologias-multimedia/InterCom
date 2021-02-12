#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (compress0.py). '''

import zlib
import numpy as np
import struct
import math
import minimal
import compress

class Compression0(compress.Compression):
    '''Compress the chunks (playing forma) with zlib.'''
    def __init__(self):
        if __debug__:
            print("Running Compression0.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (Compression0) is running")

    def pack(self, chunk_number, chunk):
        compressed_chunk = zlib.compress(chunk)
        packed_chunk = struct.pack("!H", chunk_number) + compressed_chunk
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        compressed_chunk = packed_chunk[2:]
        chunk = zlib.decompress(compressed_chunk)
        chunk = np.frombuffer(chunk, dtype=np.int16)
        chunk = chunk.reshape((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS))
        return chunk_number, chunk

class Compression0__verbose(Compression0, compress.Compression__verbose):
    def __init__(self):
        if __debug__:
            print("Running Compression0__verbose.__init__")
        super().__init__()

    def unpack(self, packed_chunk):
        len_packed_chunk = len(packed_chunk)
        self.bps[0] += len_packed_chunk*4
        self.bps[1] += len_packed_chunk*4
        return Compression0.unpack(self, packed_chunk)

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

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
        intercom = Compression0__verbose()
    else:
        intercom = Compression0()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
