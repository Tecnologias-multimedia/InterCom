#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (compress3b.py). '''

import zlib
import numpy as np
import struct
import math
import minimal
import compress

class Compression3b(compress.Compression):
    '''Chunk compression by byte-planes. 32 bits/sample. 4 code-streams.

    '''
    def __init__(self):
        if __debug__:
            print(self.__doc__)
        super().__init__()

    def pack(self, chunk_number, chunk):
        channel_0_MSB2 = (chunk[:, 0] // (1<<24)).astype(np.int8)
        channel_0_MSB1 = (chunk[:, 0] // (1<<16)).astype(np.uint8)
        channel_0_MSB0 = (chunk[:, 0] // (1<<8)).astype(np.uint8)
        channel_0_LSB  = (chunk[:, 0] % (1<<8)).astype(np.uint8)
        channel_1_MSB3 = (chunk[:, 1] // (1<<24)).astype(np.int8)
        channel_1_MSB2 = (chunk[:, 1] // (1<<16)).astype(np.uint8)
        channel_1_MSB0 = (chunk[:, 1] // (1<<8)).astype(np.int8)
        channel_1_LSB  = (chunk[:, 1] % (1<<8)).astype(np.uint8)
        MSB2 = np.concatenate([channel_0_MSB2, channel_1_MSB2])
        MSB1 = np.concatenate([channel_0_MSB1, channel_1_MSB1])
        MSB0 = np.concatenate([channel_0_MSB0, channel_1_MSB0])
        LSB  = np.concatenate([channel_0_LSB, channel_1_LSB])
        compressed_MSB2 = zlib.compress(MSB2)
        compressed_MSB1 = zlib.compress(MSB1)
        compressed_MSB0 = zlib.compress(MSB0)
        compressed_LSB  = zlib.compress(LSB)
        packed_chunk = struct.pack("!HHHH", chunk_number, len(compressed_MSB2, len(comressed_MSB1), len(compressed_MSB0)) + compressed_MSB2 + compressed_MSB1 + compressed_MSB0 + compressed_LSB 
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB2, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHHH", packed_chunk[:8])
        offset = 8 # Header size
        compressed_MSB2 = packed_chunk[offset : len_compressed_MSB2 + offset]
        offset += len_compressed_MSB2
        compressed_MSB1 = packed_chunk[offset : len_compressed_MSB1 + offset]
        offset += len_compressed_MSB1 
        compressed_MSB0 = packed_chunk[offset : len_compressed_MSB0 + offset]
        offset += len_compressed_MSB0 
        compressed_LSB = packed_chunk[offset :]
        buffer_MSB2 = zlib.decompress(compressed_MSB2)
        buffer_MSB1 = zlib.decompress(compressed_MSB1)
        buffer_MSB0 = zlib.decompress(compressed_MSB0)
        buffer_LSB  = zlib.decompress(compressed_LSB)
        channel_MSB2 = np.frombuffer(buffer_MSB2, dtype=np.int8)
        channel_MSB1 = np.frombuffer(buffer_MSB1, dtype=np.uint8)
        channel_MSB0 = np.frombuffer(buffer_MSB0, dtype=np.uint8)
        channel_LSB  = np.frombuffer(buffer_LSB, dtype=np.uint8)
        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=np.int32)
        chunk[:, 0] = channel_MSB2[:len(channel_MSB2)//2]*(1<<24) + channel_MSB1[:len(channel_MSB1)//2]*(1<<16) + channel_MSB0[:len(channel_MSB0)//2]*(1<<8) + channel_LSB[:len(channel_MSB)//2]
        chunk[:, 1] = channel_MSB2[len(channel_MSB2)//2:]*(1<<24) + channel_MSB1[len(channel_MSB1)//2:]*(1<<16) + channel_MSB0[len(channel_MSB0)//2:]*(1<<8) + channel_LSB[len(channel_MSB)//2:]
        return chunk_number, chunk

class Compression3b__verbose(Compression3, compress.Compression__verbose):

    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB2, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHHH", packed_chunk[:8])
        len_compressed_LSB = len(packed_chunk) - (len_compressed_MSB2 + len_compressed_MSB1 + len_compressed_MSB0 + 8)

        self.bps[3] += len_compressed_MSB2*8
        self.bps[2] += len_compressed_MSB1*8
        self.bps[1] += len_compressed_MSB0*8
        self.bps[0] += len_compressed_LSB*8
        return Compression3b.unpack(self, packed_chunk)

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
        intercom = Compression3__verbose()
    else:
        intercom = Compression3()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
