#
# Buffer
#
# The buffer class implements the mechanisms required to solve the jitter issues
# The ADT used is a circular queue that stores the packed received by the other
# interlocutor. The main purpose is to decrement the jitter effects by increasing
# the latency. In order to ensure that the queue has enough chunks to mitigate
# the jitter, the queue should be half filled. For that reason the initialisation
# waits to fill the half of the queue. A blank chunk with silence is played as
# a last resort in case to not have any chunk.


# import numpy as np
# Package to use several math functions
import math

# Package to performs conversions between Python values and C structs represented
# as Python strings
import struct

# Buffer is based by extending minimal class
from minimal import *
#import minimal

class Buffer(Minimal):
    """
    Class that implements the buffer required to reduce the effect of the jitter.
    Inherits from Minimal used in Milestone 5
    """

    MAX_CHUNK = 65536
    """(int) (static): Max chunk size"""

    BUFFER_SIZE = 8
    """(int) (static): Buffer size by default"""

    def __init__(self):
        """
        Class constructor

        The constructor class requires several arguments that must be provided before
        to get an buffer instance. The constructor calls the constructor of Minimal class
        and also creates all variables needed, including the buffer array.
        """

        super().__init__()

        self.jitter_to_chunk_time = math.ceil(args.jitter / (self.chunk_time * 1000))
        """(int) Result to convert jitter time to chunks size"""

        self.buffer_size = 2 * self.jitter_to_chunk_time
        """(int) Size of the buffer. It is the double of jitter_to_chunk_time"""

        self.filled_cells = 0
        """(int) Number of filled cells in the buffer"""

        self.head_cell = np.uint16(0)
        """(int) Position of the front in the queue"""

        self.tail_cell = np.uint16(0)
        """(int) Position of the rear in the queue"""

        # Print minimal information to visualize initialisation
        print("Chunk time: ", self.chunk_time * 1000)
        print("Jitter to chunk: ", self.jitter_to_chunk_time)
        print("Tamaño buffer: ", self.buffer_size)

        self.current_cell = np.uint16(0) #(self.buffer_size / 2)

        self.to_u16 = lambda x : np.uint16(x)
        """(lambda) Lambda function to cast to 16 bits unsigned integer"""

        self.update_head = lambda: self.to_u16((self.head_cell + 1) % Buffer.MAX_CHUNK)
        """(lambda) Lambda function to update (increase) the front of the queue"""

        self.update_tail = lambda: self.to_u16((self.tail_cell + 1) % Buffer.MAX_CHUNK)
        """(lambda) Lambda function to update (increase) the rearof the queue"""

        self.update_cell = lambda: self.to_u16((self.current_cell + 1) % Buffer.MAX_CHUNK)
        """(lambda) Lambda function to update (increase) the current of the queue"""

        self.index_package = lambda chunk_sequence: self.to_u16(chunk_sequence % self.buffer_size)
        """(lambda) Lambda function to calculate the position of the package in the queue"""

        # For struct mode a format must be provided Falla -> Duplicar tamaño
        self.pack_format = f"H{args.frames_per_chunk*2}h" #FIXME
        """(string) The format used in struct methods"""

        #self.format_pack = f"i{args.frames_per_chunk * self.NUMBER_OF_CHANNELS * np.dtype(self.SAMPLE_TYPE).itemsize}"

        # Create fixed empty array
        self.buffer = [None] * self.buffer_size
        """(list) A list that stores the buffer"""

        for i in range(len(self.buffer)):
            self.buffer[i] = self.zero_chunk

        self.half_buffer = False
        """(Boolean) Controls the initial state of the buffer that requires to be half-filled"""

    # TODO THIS IS THE CALLBACK
    def record_send_and_play(self, indata, outdata, frames, time, status):
        """ Callback function used by Sounddevice

        In non blocking audio stream, a new thread is created
        and periodically executes the callback method. Usually
        the call occurs when new input data (indata) is available to
        manipulate. Is recommended to manage output stream in the callback
        method also.

        The arguments are imposed to Sounndevice callback signature

        """
        self.send(indata)
        self.play(outdata)

    def play(self, outdata):
        """ Places the next chunk of audio in output streams

            Calculates the position of next cell in buffer an retrieves it
            in order to assign to the outdata stream.
        Parameters
        ----------
            outdata
                Output stream used by Sounddevice
        """
        if not self.half_buffer:
            to_play = self.zero_chunk
            # print("Executing ZERO #####")
        else:
            # print("Executing buffer #####")
            position = self.head_cell % self.buffer_size
            to_play = self.buffer[position]
            self.buffer[position] = self.zero_chunk
        outdata[:] = to_play
        # self.current_cell = self.update_cell()
        self.head_cell = self.update_head()

    # TODO EXECUTES IN MAIN THREAD
    def receive_and_buffer(self):
        """ Reveived data from the socket and stores it in the buffer

            This method is executed in the main thread in a loop. It tries to retrieve
            data from the socket. If a packet is found in the buffer, the method
            extracts the sequence number and the payload. Converts the payload in a
            suitable numpy array an then stores it in the buffer uysing the sequence
            number provided.
        """
        received = True
        # print("RECEPCIÓN")
        try:
            packed_data = self.receive()
            #chunk_index, data = struct.unpack(self.pack_format, packed_data)
            unpacked_data = struct.unpack(self.pack_format, packed_data)
            #data = np.frombuffer(data, dtype=np.int16).reshape(args.frames_per_chunk + 1, Buffer.NUMBER_OF_CHANNELS)
            chunk_index = self.to_u16(unpacked_data[0])
            # print("Antes de bloqueo")
            # print(data)
            #data = unpacked_data[1]
            data = np.array(unpacked_data[1:])
            data = data.reshape(args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
            #data = np.frombuffer(data, self.SAMPLE_TYPE).reshape(args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
            #data = data[1:,:] # FIXME REVISAR Y REPARAR, EL FALLO ESTA AQUI. ESTABA EN [1,:]
            # print("Datos recibidos")
        except socket.timeout:
            #print("Movidote de to xungo en recibir")
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
        """Starts sounddevice audio stream via callback method"""
        with sd.Stream(samplerate=args.frames_per_second, blocksize=args.frames_per_chunk, dtype=self.SAMPLE_TYPE, channels=self.NUMBER_OF_CHANNELS, callback=self.record_send_and_play):
            while True:
                self.receive_and_buffer()

    def send(self, data):
        """ Send data over sender socket

            Uses parent's method to send data.

            Parameters
            ----------
                data
                    Data to send over UDP socket. A numpy array is expected
        """
        # astype is needed to avoid implicit casting to int32
        # chunk = np.concatenate(([[self.head_cell, 0]], data)).astype(np.int16)

        chunk = struct.pack(self.pack_format, self.head_cell, *(data.flatten()))
       # print("Cabecera: ", self.head_cell)
       # print("Datos concatenados", chunk)
        super().send(chunk)
        #self.head_cell = self.update_head()
        # print("Cabecera: ", self.head_cell)

if __name__ == "__main__":
"""    parser.description = __doc__
    try:
        argcomplete.autocomplete(parser)
    except Exception:
        print("argcomplete not working :-/")
    args = parser.parse_known_args()[0]
"""
    if args.show_stats or args.show_samples:
        intercom = Buffer()
    else:
        intercom = Buffer()
    try:
        intercom.run()
    except KeyboardInterrupt:
        parser.exit("\nInterrupted by user")