"""
    compress.py

    Buffered intercom with compression.

    Compression class tries to reduce bitrate impact by compressing audio
    chunk. The compression reduces de size of the payload sent over the
    network.
"""

# Used to compress and decompress using DEFLATE
import zlib

# Required to reuse Buffered intercom
import buffer
from buffer import minimal as mini

# Instead of importing from other modules
# its easier (but maybe not perfect) reimport
import struct
import numpy as np

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

# New parameters are generated to grant flexibility
mini.parser.add_argument("-cl", "--compression_level", type=int, default=1, help="Compression level")
mini.parser.add_argument("-ndc", "--dual_channel", type=int, default=1, help="Dual channel")

class Compression(buffer.Buffering):
    """
    Class that implements a new buffered intercom with compression capabilities
    in order to reduce the bitrate effect.
    """


    def __init__(self):
        """ Class constructor.

        The constructor class requires several arguments that must be provided before
        to get a compression instance. The constructor calls the constructor of Buffer class
        and also creates all variables needed, including the buffer array.
        """
        super().__init__()
        if ((buffer.minimal.args.compression_level < 0) or (buffer.minimal.args.compression_level > 9)):
            mini.args.compression_level = 1

        self.compression_level = mini.args.compression_level
        """(int) Level used by zlib to determinate compression."""

        print("Compression level: ", mini.args.compression_level)

        self.sender_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk * mini.Minimal.NUMBER_OF_CHANNELS], dtype=np.int16)
        """(numpy array) Array used to store the arranged chunk before compression."""

        self.receiver_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk, mini.Minimal.NUMBER_OF_CHANNELS], dtype = np.int16)
        """(numpy array) Array used to store the arranged chunk after compression."""

        self.sender_buf_size = len(self.sender_chunk_buffer)
        """(int) Size of the sender_chunk_buffer."""

        self.receiver_buf_size = len(self.receiver_chunk_buffer)
        """(int) Size of the sender_chunk_buffer."""

        self.channel_size = buffer.minimal.args.frames_per_chunk
        """(int) Number of frames per chunk in each channel."""


    def pack(self, chunk_number, chunk):
        """ Pack function (Override)

            Packs the chunk by joining the sequence number used by the buffer
            and the compressed output audio stream. To increase the compression
            rate, the output is arranged by joining the cells into the same
            channel in a consecutive array.

            Parameters
            ----------
                chunk_number
                    Sequence of the chunk to send.
                chunk
                    Audio output to send.
        """

        # Join all frames ordering by channel
        if(buffer.minimal.args.dual_channel==1):
            self.sender_chunk_buffer[0: self.sender_buf_size // 2] = chunk[:, 0]
            self.sender_chunk_buffer[self.sender_buf_size // 2 : self.sender_buf_size] = chunk[:, 1]
        else:
            for i in range(0, mini.Minimal.NUMBER_OF_CHANNELS):
                self.sender_chunk_buffer[i * self.channel_size : (i + 1) * self.channel_size] = chunk[:, i]

        # Compress the arranged chunk
        packed_chunk = zlib.compress(self.sender_chunk_buffer, self.compression_level)

        # Join the sequence number and the arranged chunk
        packed_chunk = struct.pack("!H", chunk_number) + packed_chunk

        # Return the packed chunk
        return packed_chunk


    def unpack(self, packed_chunk, dtype=buffer.minimal.Minimal.SAMPLE_TYPE):
        """ Unpack function (Override)

            Unpack the chunk by extracting the sequence number and decompressing
            the compressed payload. The decompressed chunk must be rearranged
            to retrieve the original oudio.

            Parameters
            ----------
                packed_chunk
                    The payload extracted from the UDP socket.
                dtype
                    The type used in sounddevice stream. Used to rearrange the
                    retrieved chunk.
        """
        # Extract the sequence number of the chunk
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])

        # Extract the compressed chunk
        unpacked_chunk = packed_chunk[2:]

        # Decompress the chunk
        unpacked_chunk = zlib.decompress(unpacked_chunk)

        # Convert to numpy array
        decompressed = np.frombuffer(unpacked_chunk, dtype=dtype)

        # Rearrange the chunk
        if(buffer.minimal.args.dual_channel):
            self.receiver_chunk_buffer[:, 0] = decompressed[0 : len(decompressed) // 2]
            self.receiver_chunk_buffer[:, 1] = decompressed[(len(decompressed) // 2): len(decompressed)]
        else:
            for i in range(0, mini.Minimal.NUMBER_OF_CHANNELS):
                self.receiver_chunk_buffer[:, i] = decompressed[i * self.channel_size: (i+1) * self.channel_size ]

        # Other way to rearrange the chunk by joining columns. Estimated to be less inefficient
        # than using numpy slices
        # chunk = np.column_stack((decompressed[0 : int(len(decompressed)/2)], decompressed[int(len(decompressed)/2)
        # : int(len(decompressed))]))

        # Return the sequence number an the original chunk
        return chunk_number, self.receiver_chunk_buffer


class Compression__verbose(Compression, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()

if __name__ == "__main__":
    buffer.minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(buffer.minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    buffer.minimal.args = buffer.minimal.parser.parse_known_args()[0]
    if buffer.minimal.args.show_stats or buffer.minimal.args.show_samples:
        intercom = Compression__verbose()
    else:
        intercom = Compression()
    try:
        intercom.run()
    except KeyboardInterrupt:
        buffer.minimal.parser.exit("\nInterrupted by user")
