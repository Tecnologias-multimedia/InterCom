#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Compress the chunks using DEFLATE. Searialize the channels (remove samples interleaving). One DEFLATE interation per chunk.'''

import zlib
import numpy as np
import struct
import math
import logging

import minimal
import DEFLATE_raw

class DEFLATE_Serial(DEFLATE_raw.DEFLATE_Raw):
    
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

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
        chunk = chunk.reshape((minimal.args.number_of_channels, minimal.args.frames_per_chunk))
        reordered_chunk = np.empty((minimal.args.frames_per_chunk*2, ), dtype=np.int16)
        reordered_chunk[0::2] = chunk[0, :]
        reordered_chunk[1::2] = chunk[1, :]
        chunk = reordered_chunk.reshape((minimal.args.frames_per_chunk, minimal.args.number_of_channels))
        return chunk_number, chunk

class DEFLATE_Serial__verbose(DEFLATE_Serial, DEFLATE_raw.DEFLATE_Raw__verbose):
    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        len_packed_chunk = len(packed_chunk)
        self.bps[0] += len_packed_chunk*4
        self.bps[1] += len_packed_chunk*4
        return DEFLATE_Serial.unpack(self, packed_chunk)

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
        intercom = DEFLATE_Serial__verbose()
    else:
        intercom = DEFLATE_Serial()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
