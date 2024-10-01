#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Compress each raw chunk using DEFLATE.'''

import zlib
import numpy as np
import struct
import math
import logging

import minimal
import buffer

class DEFLATE_Raw(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def pack(self, chunk_number, chunk):
        compressed_chunk = zlib.compress(chunk)
        packed_chunk = struct.pack("!H", chunk_number) + compressed_chunk
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        compressed_chunk = packed_chunk[2:]
        chunk = zlib.decompress(compressed_chunk)
        chunk = np.frombuffer(chunk, dtype=np.int16)
        try:
            chunk = chunk.reshape((minimal.args.frames_per_chunk, minimal.args.number_of_channels))
        except ValueError:
            logging.warning("Input exhausted! :-/")
            self.input_exhausted = True
        return chunk_number, chunk

class DEFLATE_Raw__verbose(DEFLATE_Raw, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()
        self.standard_deviation = np.zeros(minimal.args.number_of_channels) # Standard_Deviation of the chunks_per_cycle chunks.
        self.entropy = np.zeros(minimal.args.number_of_channels) # Entropy of the chunks_per_cycle chunks.
        self.bps = np.zeros(minimal.args.number_of_channels) # Bits Per Symbol of the chunks_per_cycle compressed chunks.
        self.chunks_in_the_cycle = []

        self.average_standard_deviation = np.zeros(minimal.args.number_of_channels)
        self.average_entropy = np.zeros(minimal.args.number_of_channels)
        self.average_bps = np.zeros(minimal.args.number_of_channels)

    def stats(self):
        string = super().stats()
        string += " {}".format(['{:6.0f}'.format(i) for i in self.standard_deviation])
        string += " {}".format(['{:4.1f}'.format(i) for i in self.entropy])
        string += " {}".format(['{:4.1f}'.format(i/self.frames_per_cycle) for i in self.bps])
        return string

    def first_line(self):
        string = super().first_line()
        string += "{:>21s}".format("input audio") # standard_deviation
        string += "{:>17s}".format('input audio') # entropy
        string += "{:>17s}".format('output') # bps
        return string

    def second_line(self):
        string = super().second_line()
        string += "{:>21s}".format("standard deviation") # standard_deviation
        string += "{:>17s}".format("entropy") # entropy
        string += "{:>17s}".format("bits/sample") # bps
        return string

    def separator(self):
        string = super().separator()
        string += f"{'='*(21+17*2)}"
        return string

    def averages(self):
        string = super().averages()
        string += " {}".format(['{:6.0f}'.format(i) for i in self.average_standard_deviation])
        string += " {}".format(['{:4.1f}'.format(i) for i in self.average_entropy])
        string += " {}".format(['{:4.1f}'.format(i/self.frames_per_cycle) for i in self.average_bps])
        return string
        
    def entropy_in_bits_per_symbol(self, sequence_of_symbols):
        value, counts = np.unique(sequence_of_symbols, return_counts = True)
        probs = counts / len(sequence_of_symbols)
        #n_classes = np.count_nonzero(probs)

        #if n_classes <= 1:
        #    return 0

        entropy = 0.
        for i in probs:
            entropy -= i * math.log(i, 2)

        return entropy

    def cycle_feedback(self):
        try:
            concatenated_chunks = np.vstack(self.chunks_in_the_cycle)
        except ValueError:
            concatenated_chunks = np.vstack([self.zero_chunk, self.zero_chunk])
        self.standard_deviation = np.sqrt(np.var(concatenated_chunks, axis=0))
        self.average_standard_deviation = self.moving_average(self.average_standard_deviation, self.standard_deviation, self.cycle)

        self.entropy[0] = self.entropy_in_bits_per_symbol(concatenated_chunks[:, 0])
        self.entropy[1] = self.entropy_in_bits_per_symbol(concatenated_chunks[:, 1])
        self.average_entropy = self.moving_average(self.average_entropy, self.entropy, self.cycle)

        self.average_bps = self.moving_average(self.average_bps, self.bps, self.cycle)

        super().cycle_feedback()
        self.chunks_in_the_cycle = []
        self.bps = np.zeros(minimal.args.number_of_channels)
        
    def _record_io_and_play(self, indata, outdata, frames, time, status):
        super()._record_io_and_play(indata, outdata, frames, time, status)
        self.chunks_in_the_cycle.append(indata)
        # Remember: indata contains the recorded chunk and outdata,
        # the played chunk.

    def _read_io_and_play(self, outdata, frames, time, status):
        read_chunk = super()._read_io_and_play(outdata, frames, time, status)
        self.chunks_in_the_cycle.append(read_chunk)
        return read_chunk

    def unpack(self, packed_chunk):
        len_packed_chunk = len(packed_chunk)
        self.bps[0] += len_packed_chunk*4
        self.bps[1] += len_packed_chunk*4
        #try:
        return DEFLATE_Raw.unpack(self, packed_chunk)
        #except ValueError:
        #pass

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
        intercom = DEFLATE_Raw__verbose()
    else:
        intercom = DEFLATE_Raw()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
       intercom.print_final_averages()
