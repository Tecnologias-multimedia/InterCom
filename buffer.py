#import minimal as min
import numpy as np

import math
import struct

from minimal import *

class Buffer(Minimal):

    MAX_CHUNK = 65536
    BUFFER_SIZE = 8

    def __init__(self):
        super().__init__()

        self.jitter_to_chunk_time = math.ceil(args.jitter / (self.chunk_time * 1000))
        self.buffer_size = 2 * self.jitter_to_chunk_time
        self.filled_cells = 0
        self.head_cell = np.uint16(1)
        self.tail_cell = np.uint16(0)

        self.current_cell = np.uint16(0)

        self.to_u16 = lambda x : np.uint16(x)

        self.update_head = lambda: self.to_u16((self.head_cell + 1) % Buffer.MAX_CHUNK)
        self.update_tail = lambda: self.to_u16((self.tail_cell + 1) % Buffer.MAX_CHUNK)

        self.update_cell = lambda: self.to_u16((self.current_cell + 1) % Buffer.MAX_CHUNK)

        self.index_package = lambda chunk_sequence: self.to_u16(chunk_sequence % self.buffer_size)

        # We have 2 options to send and receive data: struct and numpy modes

        # For struct mode a format must be provided
        self.format_pack = f"i{args.frames_per_chunk * self.NUMBER_OF_CHANNELS * np.dtype(self.SAMPLE_TYPE).itemsize}"

        # Create fixed empty array
        self.buffer = [None] * self.buffer_size

        for i in range(len(self.buffer)):
            self.buffer[i] = self.zero_chunk

        self.half_buffer = False

    # TODO THIS IS THE CALLBACK
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.send(indata)
        self.play(outdata)

    def play(self, outdata):
        if not self.half_buffer :
            to_play = self.zero_chunk
            # print("Executing ZERO #####")
        else:
            # print("Executing buffer #####")
            to_play = self.buffer[self.current_cell % self.buffer_size]
            self.buffer[self.current_cell % self.buffer_size] = self.zero_chunk
            self.current_cell = self.update_cell()
        outdata[:] = to_play

    # TODO EXECUTES IN MAIN THREAD
    def receive_and_buffer(self):
        received = True
        # print("RECEPCIÓN")
        try:
            data = self.receive()
            data = np.frombuffer(data, dtype=np.int16).reshape(args.frames_per_chunk + 1, Buffer.NUMBER_OF_CHANNELS)
            chunk_index = self.to_u16(data[0,0])
            # print("Antes de bloqueo")
            # print(data)
            data = data[1:,:] # FIXME REVISAR Y REPARAR, EL FALLO ESTA AQUI. ESTABA EN [1,:]
            # print("Datos recibidos")
        except socket.timeout:
            # print("Movidote de to xungo en recibir")
            pass
        except Exception as e:
            # print("Excepción: ", e)
            pass
        else :
            # print("Almacenado en buffer")
            self.buffer[chunk_index % self.buffer_size] = data
            # print("Datos pros", data)

        # print("Valor ###: ", self.buffer[int(len(self.buffer) / 2)])
        if (self.buffer[int(len(self.buffer) / 2)]) is not None:
            self.half_buffer = True

    # TODO
    def run(self):
        with sd.Stream(samplerate=args.frames_per_second, blocksize=args.frames_per_chunk, dtype=self.SAMPLE_TYPE, channels=self.NUMBER_OF_CHANNELS, callback=self.record_send_and_play):
            while True:
                self.receive_and_buffer()

    def send(self, data):
        # Chunk is a matrix with 2 rows and frames_per_chunk columns
        # astype is needed to avoid implicit casting to int32
        chunk = np.concatenate(([[self.head_cell, 0]], data)).astype(np.int16)
       # print("Cabecera: ", self.head_cell)
       # print("Datos concatenados", chunk)
        super().send(chunk)
        self.head_cell = self.update_head()
        # print("Cabecera: ", self.head_cell)

if __name__ == "__main__":
    parser.description = __doc__
    print(args)
    intercom = Buffer()
    intercom.run()
    #print(args)




