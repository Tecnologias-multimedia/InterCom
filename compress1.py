#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (compress1.py). '''

import zlib
import numpy as np
import struct
import math
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import buffer
import compress

class Compression1(compress.Compression):
    '''Compress the chunks (first channel 0, next channel 1) using only one zlib code-stream.'''
    def __init__(self):
        if __debug__:
            print("Running Compression1.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (Compression1) is running")

    def pack(self, chunk_number, chunk):
        chunk = np.stack([chunk[:, 0], chunk[:, 1]])
        compressed_chunk = zlib.compress(chunk)
        packed_chunk = struct.pack("!H", chunk_number) + compressed_chunk
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        compressed_chunk = packed_chunk[2:]
        chunk = zlib.decompress(compressed_chunk)
        chunk = np.frombuffer(chunk, dtype=np.int16)
        chunk = chunk.reshape((self.NUMBER_OF_CHANNELS, minimal.args.frames_per_chunk))
        reordered_chunk = np.empty((minimal.args.frames_per_chunk*2, ), dtype=np.int16)
        reordered_chunk[0::2] = chunk[0, :]
        reordered_chunk[1::2] = chunk[1, :]
        chunk = reordered_chunk.reshape((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS))
        return chunk_number, chunk

class Compression1__verbose(Compression1, compress.Compression__verbose):
    def __init__(self):
        if __debug__:
            print("Running Compression1__verbose.__init__")
        super().__init__()

    def unpack(self, packed_chunk):
        len_packed_chunk = len(packed_chunk)
        self.bps[0] += len_packed_chunk*4
        self.bps[1] += len_packed_chunk*4
        return Compression1.unpack(self, packed_chunk)

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
        intercom = Compression1__verbose()
    else:
        intercom = Compression1()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
