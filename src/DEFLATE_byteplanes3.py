#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Compress the least significant byte planes of the chunks using DEFLATE. The channels are consecutive (serialized). 3 code-streams (one per byte-plane) are generated.'''

import zlib
import numpy as np
import struct
import math
import logging

import minimal
import DEFLATE_raw

class DEFLATE_BytePlanes3(DEFLATE_raw.DEFLATE_Raw):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def pack(self, chunk_number, chunk):
        assert np.all( abs(chunk) < (1<<24) )
        channel_0_MSB1 = (chunk[:, 0] // (1<<16)).astype(np.int8)
        channel_0_MSB0 = (chunk[:, 0] // (1<<8)).astype(np.uint8)
        channel_0_LSB  = (chunk[:, 0] % (1<<8)).astype(np.uint8)
        channel_1_MSB1 = (chunk[:, 1] // (1<<16)).astype(np.int8)
        channel_1_MSB0 = (chunk[:, 1] // (1<<8)).astype(np.uint8)
        channel_1_LSB  = (chunk[:, 1] % (1<<8)).astype(np.uint8)
        MSB1 = np.concatenate([channel_0_MSB1, channel_1_MSB1])
        MSB0 = np.concatenate([channel_0_MSB0, channel_1_MSB0])
        LSB  = np.concatenate([channel_0_LSB, channel_1_LSB])
        compressed_MSB1 = zlib.compress(MSB1, level=zlib.Z_BEST_COMPRESSION)
        #compressed_MSB1 = zlib.compress(MSB1, level=zlib.Z_DEFAULT_COMPRESSION)
        compressed_MSB0 = zlib.compress(MSB0, level=zlib.Z_BEST_COMPRESSION)
        #compressed_MSB0 = zlib.compress(MSB0, level=zlib.Z_DEFAULT_COMPRESSION)
        compressed_LSB  = zlib.compress(LSB, level=zlib.Z_BEST_COMPRESSION)
        #compressed_LSB  = zlib.compress(LSB, level=zlib.Z_DEFAULT_COMPRESSION)
        packed_chunk = struct.pack("!HHH", chunk_number, len(compressed_MSB1), len(compressed_MSB0)) + compressed_MSB1 + compressed_MSB0 + compressed_LSB 
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHH", packed_chunk[:6])
        offset = 6 # Header size
        compressed_MSB1 = packed_chunk[offset : len_compressed_MSB1 + offset]
        offset += len_compressed_MSB1 
        compressed_MSB0 = packed_chunk[offset : len_compressed_MSB0 + offset]
        offset += len_compressed_MSB0 
        compressed_LSB = packed_chunk[offset :]
        buffer_MSB1 = zlib.decompress(compressed_MSB1)
        buffer_MSB0 = zlib.decompress(compressed_MSB0)
        buffer_LSB  = zlib.decompress(compressed_LSB)
        channel_MSB1 = np.frombuffer(buffer_MSB1, dtype=np.int8)
        channel_MSB0 = np.frombuffer(buffer_MSB0, dtype=np.uint8)
        channel_LSB  = np.frombuffer(buffer_LSB, dtype=np.uint8)
        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=np.int32)
        chunk[:, 0] = channel_MSB1[:len(channel_MSB1)//2].astype(np.uint32)*(1<<16) + channel_MSB0[:len(channel_MSB0)//2].astype(np.uint16)*(1<<8) + channel_LSB[:len(channel_LSB)//2]
        chunk[:, 1] = channel_MSB1[len(channel_MSB1)//2:].astype(np.uint32)*(1<<16) + channel_MSB0[len(channel_MSB0)//2:].astype(np.uint16)*(1<<8) + channel_LSB[len(channel_LSB)//2:]
        return chunk_number, chunk

class DEFLATE_BytePlanes3__verbose(DEFLATE_BytePlanes3, DEFLATE_raw.DEFLATE_Raw__verbose):

    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHH", packed_chunk[:6])
        len_compressed_LSB = len(packed_chunk) - (len_compressed_MSB1 + len_compressed_MSB0 + 6)

        # Ojo, que esto son los bps / byteplanes !!! (lo mismo nos vamos a sólo una medida)
        self.bps[1] += (len_compressed_MSB1 + len_compressed_MSB0)*8
        self.bps[0] += len_compressed_LSB*8
        return DEFLATE_BytePlanes3.unpack(self, packed_chunk)

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
        intercom = DEFLATE_BytePlanes3__verbose()
    else:
        intercom = DEFLATE_BytePlanes3()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
