#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Compress the least significant byte planes of the chunks using DEFLATE. The channels are interlaced. 2 code-streams (one per byte-plane) are generated'''

import zlib
import numpy as np
import struct
import math
import logging

import minimal
import DEFLATE_raw

class DEFLATE_BytePlanes2_Interlaced(DEFLATE_raw.DEFLATE_Raw):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        if minimal.args.number_of_channels != 2:
            self.pack = self.pack_mono
            self.unpack = self.unpack_mono
        else:
            self.pack = self.pack_stereo
            self.unpack = self.unpack_stereo

    def pack_stereo(self, chunk_number, chunk):
        MSB = (chunk // 256).astype(np.int8)
        LSB = (chunk % 256).astype(np.uint8)
        compressed_MSB = zlib.compress(MSB, level=zlib.Z_BEST_COMPRESSION)
        compressed_LSB = zlib.compress(LSB, level=zlib.Z_BEST_COMPRESSION)
        packed_chunk = struct.pack("!HH", chunk_number, len(compressed_MSB)) + compressed_MSB + compressed_LSB 
        return packed_chunk

    def pack_mono(self, chunk_number, chunk):
        return self.pack_stereo(chunk_number, chunk)

    def unpack_stereo(self, packed_chunk):
        (chunk_number, len_compressed_MSB) = struct.unpack("!HH", packed_chunk[:4])
        compressed_MSB = packed_chunk[4:len_compressed_MSB+4]
        compressed_LSB = packed_chunk[len_compressed_MSB+4:]
        MSB = np.frombuffer(zlib.decompress(compressed_MSB), dtype=np.int8).reshape((minimal.args.frames_per_chunk, minimal.args.number_of_channels))
        LSB = np.frombuffer(zlib.decompress(compressed_LSB), dtype=np.uint8).reshape((minimal.args.frames_per_chunk, minimal.args.number_of_channels))
        chunk = MSB.astype(np.uint16)*256 + LSB
        return chunk_number, chunk

    def unpack_mono(self, packed_chunk):
        return self.unpack_stereo(packed_chunk)

class DEFLATE_BytePlanes2_Interlaced__verbose(DEFLATE_BytePlanes2_Interlaced, DEFLATE_raw.DEFLATE_Raw__verbose):
    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])
        len_compressed_channel_1 = len(packed_chunk[len_compressed_channel_0+4:])

        self.bps[0] += len_compressed_channel_0*8
        self.bps[1] += len_compressed_channel_1*8
        return DEFLATE_BytePlanes2_Interlaced.unpack(self, packed_chunk)

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
    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = DEFLATE_BytePlanes2_Interlaced__verbose()
    else:
        intercom = DEFLATE_BytePlanes2_Interlaced()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
       intercom.print_final_averages()
