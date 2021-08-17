#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (compress3.py). '''

import zlib
import numpy as np
import struct
import math
import minimal
import compress

class Compression3(compress.Compression):
    '''Chunk compression by byte-planes. 16 bits/sample. 2 code-streams.

    '''
    def __init__(self):
        if __debug__:
            print(self.__doc__)
        super().__init__()

    def pack(self, chunk_number, chunk):
        channel_0_MSB = (chunk[:, 0] // 256).astype(np.int8)
        channel_0_LSB = (chunk[:, 0] % 256).astype(np.uint8)
        channel_1_MSB = (chunk[:, 1] // 256).astype(np.int8)
        channel_1_LSB = (chunk[:, 1] % 256).astype(np.uint8)
        MSB = np.concatenate([channel_0_MSB, channel_1_MSB])
        LSB = np.concatenate([channel_0_LSB, channel_1_LSB])
        compressed_MSB = zlib.compress(MSB)
        compressed_LSB = zlib.compress(LSB)
        packed_chunk = struct.pack("!HH", chunk_number, len(compressed_MSB)) + compressed_MSB + compressed_LSB 
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB) = struct.unpack("!HH", packed_chunk[:4])

        compressed_MSB = packed_chunk[4:len_compressed_MSB+4]
        compressed_LSB = packed_chunk[len_compressed_MSB+4:]
        buffer_MSB = zlib.decompress(compressed_MSB)
        buffer_LSB = zlib.decompress(compressed_LSB)
        channel_MSB = np.frombuffer(buffer_MSB, dtype=np.int8)
        channel_LSB = np.frombuffer(buffer_LSB, dtype=np.uint8)
        #print(channel_MSB.shape, channel_LSB.shape)
        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=np.int16)
        #print(chunk.shape)
        chunk[:, 0] = channel_MSB[:len(channel_MSB)//2]*256 + channel_LSB[:len(channel_MSB)//2]
        chunk[:, 1] = channel_MSB[len(channel_MSB)//2:]*256 + channel_LSB[len(channel_MSB)//2:]
        return chunk_number, chunk

class Compression3__verbose(Compression3, compress.Compression__verbose):

    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB) = struct.unpack("!HH", packed_chunk[:4])
        len_compressed_LSB = len(packed_chunk[len_compressed_MSB + 4 :])

        self.bps[0] += len_compressed_MSB*8
        self.bps[1] += len_compressed_LSB*8
        return Compression3.unpack(self, packed_chunk)

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
