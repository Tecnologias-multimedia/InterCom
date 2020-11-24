import buffer
from buffer import *
import zlib
import numpy as np

class Compression(Buffering):

    def pack(self, chunk_number, chunk):
        #Transforma de (1024,2) a (2,1024)
        var = chunk.ravel()
        pares = var[::2]
        impares = var[1::2]
        total = np.vstack((pares,impares))
        #print(total.shape)
        packed_chunk = struct.pack("!H", chunk_number) + total.tobytes()
        packed_chunk = zlib.compress(packed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        packed_chunk = zlib.decompress(packed_chunk)
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])
        chunk = packed_chunk[2:]
        chunk = np.frombuffer(chunk, dtype=dtype)
        dosd = chunk.reshape(self.NUMBER_OF_CHANNELS, minimal.args.frames_per_chunk )
        datos = np.arange(minimal.args.frames_per_chunk*self.NUMBER_OF_CHANNELS).reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        for i in range( minimal.args.frames_per_chunk):
            datos[i] = [dosd[0][i],dosd[1][i]]

        return chunk_number, datos

if __name__ == "__main__":
    minimal.parser.description = __doc__
    argcomplete.autocomplete(minimal.parser)
    minimal.args = minimal.parser.parse_known_args()[0]
    intercom = Compression()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
