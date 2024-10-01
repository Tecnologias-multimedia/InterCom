#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Compress the least significant byte planes of the chunks using DEFLATE. The channels are consecutive (serialized). 2 code-streams (one per byte-plane) are generated.'''

import zlib
import numpy as np
import struct
import math
import logging

import minimal
import DEFLATE_raw

class DEFLATE_BytePlanes2(DEFLATE_raw.DEFLATE_Raw):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

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
        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=np.int16)
        chunk[:, 0] = channel_MSB[:len(channel_MSB)//2].astype(np.uint16)*256 + channel_LSB[:len(channel_MSB)//2]
        chunk[:, 1] = channel_MSB[len(channel_MSB)//2:].astype(np.uint16)*256 + channel_LSB[len(channel_MSB)//2:]
        return chunk_number, chunk

class DEFLATE_BytePlanes2__verbose(DEFLATE_BytePlanes2, DEFLATE_raw.DEFLATE_Raw__verbose):

    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB) = struct.unpack("!HH", packed_chunk[:4])
        len_compressed_LSB = len(packed_chunk[len_compressed_MSB + 4 :])

        self.bps[0] += len_compressed_MSB*8
        self.bps[1] += len_compressed_LSB*8
        return DEFLATE_BytePlanes2.unpack(self, packed_chunk)

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
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = DEFLATE_BytePlanes2__verbose()
    else:
        intercom = DEFLATE_BytePlanes2()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
