#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Compress the chunks using DEFLATE. Searialize the channels (remove samples interleaving). One DEFLATE interation per channel (each byte-plane is compressed independently).'''

import zlib
import numpy as np
import struct
import math
import logging

import minimal
import DEFLATE_raw

class DEFLATE_Serial2(DEFLATE_raw.DEFLATE_Raw):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def pack(self, chunk_number, chunk):
        channel_0 = chunk[:, 0].copy()
        channel_1 = chunk[:, 1].copy()
        compressed_channel_0 = zlib.compress(channel_0)
        compressed_channel_1 = zlib.compress(channel_1)
        packed_chunk = struct.pack("!HH", chunk_number, len(compressed_channel_0)) + compressed_channel_0 + compressed_channel_1
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])

        compressed_channel_0 = packed_chunk[4:len_compressed_channel_0+4]
        compressed_channel_1 = packed_chunk[len_compressed_channel_0+4:]
        channel_0 = zlib.decompress(compressed_channel_0)
        channel_0 = np.frombuffer(channel_0, dtype=np.int16)
        channel_1 = zlib.decompress(compressed_channel_1)
        channel_1 = np.frombuffer(channel_1, dtype=np.int16)

        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=np.int16)
        chunk[:, 0] = channel_0[:]
        chunk[:, 1] = channel_1[:]

        return chunk_number, chunk

class DEFLATE_Serial2__verbose(DEFLATE_Serial2, DEFLATE_raw.DEFLATE_Raw__verbose):
    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])
        len_compressed_channel_1 = len(packed_chunk[len_compressed_channel_0+4:])

        self.bps[0] += len_compressed_channel_0*8
        self.bps[1] += len_compressed_channel_1*8
        return DEFLATE_Serial2.unpack(self, packed_chunk)

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
        intercom = DEFLATE_Serial2__verbose()
    else:
        intercom = DEFLATE_Serial2()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
