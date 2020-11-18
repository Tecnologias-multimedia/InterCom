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

        self.jitter_time = args.buffer_time

        self.jitter_to_chunk_time = math.ceil(args.buffer_time/ (self.chunk_time * 1000))
        """(int) Result to convert jitter time to chunks size"""

        self.buffer_size = 2 * self.jitter_to_chunk_time
        """(int) Size of the buffer. It is the double of jitter_to_chunk_time"""

        self.filled_cells = 0
        """(int) Number of filled cells in the buffer"""

        self.index_local_cell = np.uint16(0)
        """(int) Index of the current chunk"""

        self.index_remote_cell = np.uint16(0)
        """(int) Index of the current chunk to send"""

        self.buffer_head = np.uint16(0)
        """(int) Index of the head of the buffer"""

        # Print minimal information to visualize initialisation
        print("Chunk time: ", self.chunk_time * 1000)
        print("Jitter time: ", self.jitter_time)
        print("Jitter to chunk: ", self.jitter_to_chunk_time)
        print("Tamaño buffer: ", self.buffer_size)

        self.current_cell = np.uint16(0)

        self.to_u16 = lambda x : np.uint16(x)
        """(lambda) Lambda function to cast to 16 bits unsigned integer"""

        self.update_local_index = lambda: self.to_u16((self.index_local_cell + 1) % Buffer.MAX_CHUNK)
        """(lambda) Lambda function to update (increase) the front of the queue"""

        self.update_remote_index = lambda: self.to_u16((self.index_remote_cell + 1) % Buffer.MAX_CHUNK)
        """(lambda) Lambda function to update (increase) the rearof the queue"""

        self.index_package = lambda chunk_sequence: self.to_u16(chunk_sequence % self.buffer_size)
        """(lambda) Lambda function to calculate the position of the package in the queue"""

        self.increment_cells = lambda cells: cells + 1
        """(lambda) Lambda function to increment variable"""

        self.decrement_cells = lambda cells: cells - 1
        """(lambda) Lambda function to decrement variable"""

        self.update_head = lambda : (self.buffer_head + 1) % self.buffer_size
        """(lambda) Lambda function to update the head of the buffer"""

        self.pack_format = f"H{args.frames_per_chunk * self.NUMBER_OF_CHANNELS}h"
        """(string) The format used in struct methods"""

        # Create fixed empty array
        self.buffer = [None] * self.buffer_size
        """(list) A list that stores the buffer"""

        for i in range(len(self.buffer)):
            self.buffer[i] = self.zero_chunk

        self.half_buffer = False
        """(Boolean) Controls the initial state of the buffer that requires to be half-filled"""

    # THIS IS THE CALLBACK
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
        else:
            #position = self.index_local_cell % self.buffer_size
            to_play = self.buffer[self.buffer_head]
            self.buffer[self.buffer_head] = self.zero_chunk
            self.filled_cells = self.filled_cells - 1
            self.buffer_head = self.update_head()
            #self.index_local_cell = self.update_local_index()
        outdata[:] = to_play

    # EXECUTES IN MAIN THREAD
    def receive_and_buffer(self):
        """ Receive data from the socket and stores it in the buffer

            This method is executed in the main thread in a loop. It tries to retrieve
            data from the socket. If a packet is found in the buffer, the method
            extracts the sequence number and the payload. Converts the payload in a
            suitable numpy array an then stores it in the buffer uysing the sequence
            number provided.

            Raises
            ------
                socket.timeout
                    Resource temporarily unavailable. Socket may be empty.
                    In non-blocking UDP socket an exception of this type is raised.
        """

        try:
            packed_data = self.receive()
            unpacked_data = struct.unpack(self.pack_format, packed_data)
            chunk_index = self.to_u16(unpacked_data[0])
            data = np.array(unpacked_data[1:])
            data = data.reshape(args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        except Exception as e:
            pass
        else :
            # print("Recibiendo: ", chunk_index)
            self.buffer[chunk_index % self.buffer_size] = data
            self.filled_cells = self.filled_cells+1
            # print("Filled cells: " , self.filled_cells)
        if (self.filled_cells >= (len(self.buffer)/2)):
            self.half_buffer = True

    def start(self):
        self.sock.settimeout(0)
        """Starts sounddevice audio stream via callback method"""
        with sd.Stream(samplerate=args.frames_per_second, blocksize=args.frames_per_chunk, dtype=self.SAMPLE_TYPE, channels=self.NUMBER_OF_CHANNELS, callback=self.record_send_and_play):
            while True:
                self.receive_and_buffer()

    def send(self, data):
        """ Send data over sender socket

            Uses the method of the parent to send data.

            Parameters
            ----------
                data
                    Data to send over UDP socket. A numpy array is expected
        """
        chunk = struct.pack(self.pack_format, self.index_remote_cell, *(data.flatten()))
        # print("Enviando: ", self.index_remote_cell)
        self.index_remote_cell = self.update_remote_index()
        super().send(chunk)

if __name__ == "__main__":
    parser.description = __doc__
    try:
        argcomplete.autocomplete(parser)
    except Exception:
        print("argcomplete not working :-/")
    args = parser.parse_known_args()[0]

    if args.show_stats or args.show_samples:
        intercom = Buffer()
    else:
        intercom = Buffer()
    try:
        intercom.start()
    except KeyboardInterrupt:
        parser.exit("\nInterrupted by user")