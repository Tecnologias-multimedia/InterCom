import zlib

import buffer
from buffer import minimal as mini

import minimal

import struct
import numpy as np

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal

mini.parser.add_argument("-cl", "--compression_level", type=int, default=1, help="Compression level")
mini.parser.add_argument("-ndc", "--dual_channel", type=int, default=1, help="Dual channel")

class Compression(buffer.Buffering):

    def __init__(self):
        super().__init__()
        if ((buffer.minimal.args.compression_level < 0) or (buffer.minimal.args.compression_level > 9)):
            mini.args.compression_level = 1
        self.compression_level = mini.args.compression_level

        print("Compression level: ", mini.args.compression_level)

        #self.sender_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk, mini.Minimal.NUMBER_OF_CHANNELS], dtype = np.int16)
        self.sender_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk * mini.Minimal.NUMBER_OF_CHANNELS], dtype=np.int16)
        self.receiver_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk, mini.Minimal.NUMBER_OF_CHANNELS], dtype = np.int16)
        self.sender_buf_size = len(self.sender_chunk_buffer)
        self.receiver_buf_size = len(self.receiver_chunk_buffer)
        self.channel_size = buffer.minimal.args.frames_per_chunk


    def pack(self, chunk_number, chunk):
        # Unimos todos los frames en unico vector

        if(buffer.minimal.args.dual_channel==1):
            self.sender_chunk_buffer[0: self.sender_buf_size // 2] = chunk[:, 0]
            self.sender_chunk_buffer[self.sender_buf_size // 2 : self.sender_buf_size] = chunk[:, 1]
        else:
            for i in range(0, mini.Minimal.NUMBER_OF_CHANNELS):
                self.sender_chunk_buffer[i * self.channel_size : (i + 1) * self.channel_size] = chunk[:, i]

        #packed_chunk = np.concatenate([chunk[:,0] , chunk[:,1]])

        #Comprimimos el chunk unido
        packed_chunk = zlib.compress(self.sender_chunk_buffer, self.compression_level)

        #Unimos todo con struct
        packed_chunk = struct.pack("!H", chunk_number) + packed_chunk

        #Devolvemos el chunk
        return packed_chunk


    def unpack(self, packed_chunk, dtype=buffer.minimal.Minimal.SAMPLE_TYPE):
        #Extraemos los valores del struct

        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])

        unpacked_chunk = packed_chunk[2:]

        #Descomprimimos el chunk
        unpacked_chunk = zlib.decompress(unpacked_chunk)

        #Ajustamos el chunk a numpy
        decompressed = np.frombuffer(unpacked_chunk, dtype=np.int16)

        #print("Size buffer:", len(self.receiver_chunk_buffer))
        #print("Decompressed buffer:", len(decompressed))

        if(buffer.minimal.args.dual_channel):
        #    print("Dentro")
            self.receiver_chunk_buffer[: , 0] = decompressed[0 : len(decompressed) // 2]
            self.receiver_chunk_buffer[: , 1] = decompressed[(len(decompressed) // 2) : len(decompressed)]
        else:
            for i in range(0, mini.Minimal.NUMBER_OF_CHANNELS):
                self.receiver_chunk_buffer[: , i] = decompressed[i * self.channel_size  : (i+1) * self.channel_size ]

        # index1 = 0
        # index2 = int(len(decompressed)/2)
        # index3 = int(len(decompressed))
        # chunk = np.column_stack((decompressed[0 : int(len(decompressed)/2)], decompressed[int(len(decompressed)/2) : int(len(decompressed))]))

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
