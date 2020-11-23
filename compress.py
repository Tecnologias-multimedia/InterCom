import zlib

import buffer
import minimal

import struct
import numpy as np

import sys

class Compression(buffer.Buffering):

    def __init__(self):
        super().__init__()

    # Meter nivel de compresion


    def pack(self, chunk_number, chunk):
        # Unimos todos los frames en unico vector
        packed_chunk = np.concatenate([chunk[:,0] , chunk[:,1]])

        #Comprimimos el chunk unido
        packed_chunk = zlib.compress(packed_chunk,1)

        #Unimos todo con struct
        packed_chunk = struct.pack("!H", chunk_number) + packed_chunk

        #Devolvemos el chunk
        return(packed_chunk)


    def unpack(self, packed_chunk, dtype=buffer.minimal.Minimal.SAMPLE_TYPE):
        #Extraemos los valores del struct

        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])

        unpacked_chunk = packed_chunk[2:]

        #Descomprimimos el chunk
        unpacked_chunk = zlib.decompress(bytearray(unpacked_chunk))

        #Ajustamos el chunk a numpy
        decompressed = np.frombuffer(unpacked_chunk, dtype=np.int16)

        index1 = 0
        index2 = int(len(decompressed)/2)
        index3 = int(len(decompressed))
        chunk = np.column_stack((decompressed[0 : int(len(decompressed)/2)], decompressed[int(len(decompressed)/2) : int(len(decompressed))]))

        return chunk_number, chunk

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
