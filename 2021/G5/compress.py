#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (lossless compression of the chunks). '''

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

class Compression(buffer.Buffering):
    '''Compress the chunks. Reorder the samples into channels and compress
    them using zlib. Each channel is compressed independently.

    Methods
    -------
    pack(chunk)
    unpack(chunk)

    '''
    def __init__(self):
        '''Constructor. Configures the audio sample type.

        Parameters
        ----------
        dtype : type

            The type used for the audio samples during the
            compression/decompression.

        '''
        if __debug__:
            print("Running Compression.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (Compression) is running")

    def pack(self, chunk_number, chunk):
        '''Builds a packed packet with a compressed chunk and a chunk_number.

        Parameters
        ----------
        chunk : numpy.ndarray

            A chunk of audio.

        Returns
        -------
        bytes

            A packed chunk where only the audio (not the chunk number)
            has been compressed with DEFLATE.

        '''
        channel_0 = chunk[:, 0].copy()
        channel_1 = chunk[:, 1].copy()
        compressed_channel_0 = zlib.compress(channel_0)
        compressed_channel_1 = zlib.compress(channel_1)
        packed_chunk = struct.pack("!HH", chunk_number, len(compressed_channel_0)) + compressed_channel_0 + compressed_channel_1
        return packed_chunk
    def _pack(self, chunk_number, chunk):
        '''Only for testing purposes. Both channels are compressed at one.'''
        chunk = np.stack([chunk[:, 0], chunk[:, 1]]) # Reorder and copy audio data in a different object.
        compressed_chunk = zlib.compress(chunk)
        packed_chunk = struct.pack("!H", chunk_number) + compressed_chunk
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        '''Gets the chunk number and the chunk audio from packed_chunk.

        Parameters
        ----------
        packed_chunk : bytes

            The (chunk number, compressed chunk) structure, where
            chunk has been compressed with DEFLATE.

        Returns
        -------
        chunk_number : int

            The number of the unpacked chunk.

        chunk : numpy.ndarray

            The decompressed chunk audio.

        '''
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])

        compressed_channel_0 = packed_chunk[4:len_compressed_channel_0+4]
        compressed_channel_1 = packed_chunk[len_compressed_channel_0+4:]
        channel_0 = zlib.decompress(compressed_channel_0)
        channel_0 = np.frombuffer(channel_0, dtype)
        channel_1 = zlib.decompress(compressed_channel_1)
        channel_1 = np.frombuffer(channel_1, dtype)

        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=dtype)
        chunk[:, 0] = channel_0[:]
        chunk[:, 1] = channel_1[:]

        return chunk_number, chunk
    def _unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        compressed_chunk = packed_chunk[2:]
        chunk = zlib.decompress(compressed_chunk)
        chunk = np.frombuffer(chunk, dtype)
        chunk = chunk.reshape((self.NUMBER_OF_CHANNELS, minimal.args.frames_per_chunk))
        reordered_chunk = np.empty((minimal.args.frames_per_chunk*2, ), dtype=dtype)
        reordered_chunk[0::2] = chunk[0, :]
        reordered_chunk[1::2] = chunk[1, :]
        chunk = reordered_chunk.reshape((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS))
        return chunk_number, chunk

class Compression__verbose(Compression, buffer.Buffering__verbose):
    def __init__(self):
        if __debug__:
            print("Running Compression__verbose.__init__")
        super().__init__()
        self.variance = np.zeros(self.NUMBER_OF_CHANNELS) # Variance of the chunks_per_cycle chunks.
        self.entropy = np.zeros(self.NUMBER_OF_CHANNELS) # Entropy of the chunks_per_cycle chunks.
        self.bps = np.zeros(self.NUMBER_OF_CHANNELS) # Bits Per Symbol of the chunks_per_cycle compressed chunks.
        self.chunks_in_the_cycle = []

        self.average_variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_entropy = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_bps = np.zeros(self.NUMBER_OF_CHANNELS)

    def stats(self):
        string = super().stats()
        string += " {}".format(['{:9.0f}'.format(i) for i in self.variance])
        string += " {}".format(['{:4.1f}'.format(i) for i in self.entropy])
        string += " {}".format(['{:4.1f}'.format(i/self.frames_per_cycle) for i in self.bps])
        return string

    def first_line(self):
        string = super().first_line()
        string += "{:27s}".format('') # variance
        string += "{:17s}".format('') # entropy
        string += "{:17s}".format('') # bps
        return string

    def second_line(self):
        string = super().second_line()
        string += "{:>27s}".format("variance") # variance
        string += "{:>17s}".format("entropy") # entropy
        string += "{:>17s}".format("BPS") # bps
        return string

    def separator(self):
        string = super().separator()
        string += f"{'='*(27+17*2)}"
        return string

    def averages(self):
        string = super().averages()
        string += " {}".format(['{:9.0f}'.format(i) for i in self.average_variance])
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
        
        self.variance = np.var(concatenated_chunks, axis=0)
        self.average_variance = self.moving_average(self.average_variance, self.variance, self.cycle)

        self.entropy[0] = self.entropy_in_bits_per_symbol(concatenated_chunks[:, 0])
        self.entropy[1] = self.entropy_in_bits_per_symbol(concatenated_chunks[:, 1])
        self.average_entropy = self.moving_average(self.average_entropy, self.entropy, self.cycle)

        self.average_bps = self.moving_average(self.average_bps, self.bps, self.cycle)

        super().cycle_feedback()
        self.chunks_in_the_cycle = []
        self.bps = np.zeros(self.NUMBER_OF_CHANNELS)
        
    def _record_send_and_play(self, indata, outdata, frames, time, status):
        super()._record_send_and_play(indata, outdata, frames, time, status)
        self.chunks_in_the_cycle.append(indata)
        # Remember: indata contains the recorded chunk and outdata,
        # the played chunk.

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])
        len_compressed_channel_1 = len(packed_chunk[len_compressed_channel_0+4:])

        self.bps[0] += len_compressed_channel_0*8
        self.bps[1] += len_compressed_channel_1*8
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        return chunk_number, chunk

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
        intercom = Compression__verbose()
    else:
        intercom = Compression()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
