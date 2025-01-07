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
        #assert np.all( abs(chunk) < (1<<24) )
        channel_LSB  = [None]*minimal.args.number_of_channels
        channel_MSB0 = [None]*minimal.args.number_of_channels
        channel_MSB1 = [None]*minimal.args.number_of_channels
        for i in range(minimal.args.number_of_channels):
            channel_MSB1[i] = (chunk[:, i].astype(np.int32) // (1<<16)).astype(np.int8)
            channel_MSB0[i] = (chunk[:, i] // (1<<8)).astype(np.uint8)
            channel_LSB [i] = (chunk[:, i] % (1<<8)).astype(np.uint8)
        MSB1 = np.concatenate(channel_MSB1)
        MSB0 = np.concatenate(channel_MSB0)
        LSB  = np.concatenate(channel_LSB )
        compressed_MSB1 = zlib.compress(MSB1, level=zlib.Z_BEST_COMPRESSION)
        #compressed_MSB1 = zlib.compress(MSB1, level=zlib.Z_DEFAULT_COMPRESSION)
        compressed_MSB0 = zlib.compress(MSB0, level=zlib.Z_BEST_COMPRESSION)
        #compressed_MSB0 = zlib.compress(MSB0, level=zlib.Z_DEFAULT_COMPRESSION)
        compressed_LSB  = zlib.compress(LSB, level=zlib.Z_BEST_COMPRESSION)
        #compressed_LSB  = zlib.compress(LSB, level=zlib.Z_DEFAULT_COMPRESSION)
        packed_chunk = struct.pack("!HHH", chunk_number, len(compressed_MSB1), len(compressed_MSB0)) + compressed_MSB1 + compressed_MSB0 + compressed_LSB 
        return packed_chunk

    def unpack(self, packed_chunk):
        offset = 6 # Header size
        (chunk_number, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHH", packed_chunk[:offset])
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
        chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for i in range(minimal.args.number_of_channels):
            chunk[:, i] = \
                channel_MSB1[:len(channel_MSB1)//minimal.args.number_of_channels].astype(np.uint32)*(1<<16) + \
                channel_MSB0[:len(channel_MSB0)//minimal.args.number_of_channels].astype(np.uint16)*(1<<8) + \
                channel_LSB[:len(channel_LSB)//minimal.args.number_of_channels]
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
