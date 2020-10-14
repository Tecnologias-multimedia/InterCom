import argparse

# Handle the sound card. See:
# https://python-sounddevice.readthedocs.io
try:
    import sounddevice as sd
except ModuleNotFoundError:
    import os
    os.system("pip3 install sounddevice --user")
    import sounddevice as sd

# Provides efficient arrays. See: https://numpy.org
try:
    import numpy as np
except ModuleNotFoundError:
    print("Installing numpy with pip")
    import os
    os.system("pip3 install numpy --user")
    import numpy as np

# Socket API for interprocess communications through the Internet. See:
# https://docs.python.org/3/library/socket.html
import socket

from multiprocessing import Process

class Intercom_minimal:
    
    # Default audio configuration. See:
    # https://nbviewer.jupyter.org/github/vicente-gonzalez-ruiz/YAPT/blob/master/multimedia/sounddevice.ipynb
    
    # 1 = mono, 2 = stereo.
    NUMBER_OF_CHANNELS = 2

    # Sampling frequency (44100 Hz -> CD quality). A frame is a
    # structure:
    #
    # frame {
    #   [number_of_channels] int16 sample;
    # }
    FRAMES_PER_SECOND = 44100

    # Number of frames per chunk of audio interchanged with the sound
    # card.
    FRAMES_PER_CHUNK = 1024

    # Default network configuration. See: 

    # Maximum size of the
    # [payload](https://en.wikipedia.org/wiki/User_Datagram_Protocol)
    # of a transmitted packet. This parameter is used by the OS to
    # allocate memory for incomming packets. Notice that this value
    # limites the maximum length (in bytes) of a chunk.
    MAX_PAYLOAD_BYTES = 32768

    # [Port](https://en.wikipedia.org/wiki/Port_(computer_networking))
    # that my machine will use to listen to the incomming packets.
    MY_PORT = 4444

    # Port that my interlocutor's machine will use to listen to the
    # incomming packets.
    DESTINATION_PORT = 4444

    # [Hostname](https://en.wikipedia.org/wiki/Hostname) or [IP
    # address](https://en.wikipedia.org/wiki/IP_address) of my
    # interlocutor's
    # [host](https://en.wikipedia.org/wiki/Host_(network)).
    DESTINATION_ADDRESS = "localhost"

    def init(self, args):
        
        # Gathers the information provided by the args object, and
        # initializes other structures, such as the socket and the
        # queue.

        # Command-line parameters. Notice that args is only an
        # argument for init(), not for the rest of methods.
        self.number_of_channels = args.number_of_channels
        self.frames_per_second = args.frames_per_second
        self.frames_per_chunk = args.frames_per_chunk
        self.my_port = args.my_port
        self.destination_address = args.destination_address 
        self.destination_port = args.destination_port

        # Data type used for NumPy arrays, which defines the number of
        # bits per sample. See:
        # https://numpy.org/devdocs/user/basics.types.html
        self.sample_type = np.int16

        self.samples_per_chunk = self.frames_per_chunk * self.number_of_channels
        self.bytes_per_chunk = self.samples_per_chunk * np.dtype(self.sample_type).itemsize
        assert self.bytes_per_chunk <= Intercom_minimal.MAX_PAYLOAD_BYTES, \
          f"bytes_per_chunk={self.bytes_per_chunk} > MAX_PAYLOAD_BYTES={Intercom_minimal.MAX_PAYLOAD_BYTES}"

        # Sending and receiving sockets creation and configuration for
        # UDP traffic. See:
        # https://wiki.python.org/moin/UdpCommunication
        self.sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", self.my_port)
        self.receiving_sock.bind(self.listening_endpoint)

        print(f"Intercom_minimal: number_of_channels={self.number_of_channels}")
        print(f"Intercom_minimal: frames_per_second={self.frames_per_second}")
        print(f"Intercom_minimal: frames_per_chunk={self.frames_per_chunk}")
        print(f"Intercom_minimal: samples_per_chunk={self.samples_per_chunk}")
        print(f"Intercom_minimal: my_port={self.my_port}")
        print(f"Intercom_minimal: destination_address={self.destination_address}")
        print(f"Intercom_minimal: destination_port={self.destination_port}")
        print(f"Intercom_minimal: bytes_per_chunk={self.bytes_per_chunk}")

        # A received chunk is stored in this statically-allocated
        # memory to avoid the creation of a new object for each
        # reception. This empty chunk has also the structure necessary
        # to send it to sounddevice, which is:
        #
        # chunk {
        #   int16 [frames_per_chunk][number_of_channels] sample;
        # }
        #
        self.zero_chunk = self.generate_zero_chunk()
        payload_structure = f"{self.frames_per_chunk * self.number_of_channels}h"

        print("Intercom_minimal: running ...")

    def run(self):
        with sd.Stream(samplerate=self.frames_per_second,
                       blocksize=self.frames_per_chunk,
                       dtype=np.int16,
                       channels=self.number_of_channels,
                       callback=self.record_send_play):
            print("Intercom_minimal: press <CTRL> + <c> to quit")
            input()
            
    # Define the command-line arguments.
    def add_args(self):
        parser = argparse.ArgumentParser(description="Real-Time Audio Intercommunicator",
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-s", "--frames_per_chunk",
                            help="Number of frames (stereo samples) per chunk.",
                            type=int, default=Intercom_minimal.FRAMES_PER_CHUNK)
        parser.add_argument("-r", "--frames_per_second",
                            help="Sampling rate in frames/second.",
                            type=int, default=Intercom_minimal.FRAMES_PER_SECOND)
        parser.add_argument("-c", "--number_of_channels",
                            help="Number of channels.",
                            type=int, default=Intercom_minimal.NUMBER_OF_CHANNELS)
        parser.add_argument("-p", "--my_port",
                            help="My listening port.",
                            type=int, default=Intercom_minimal.MY_PORT)
        parser.add_argument("-i", "--destination_port",
                            help="Interlocutor's listening port.",
                            type=int, default=Intercom_minimal.DESTINATION_PORT)
        parser.add_argument("-a", "--destination_address",
                            help="Interlocutor's IP address or name.",
                            type=str, default=Intercom_minimal.DESTINATION_ADDRESS)
        return parser
    
    # The audio driver never stops recording and playing. Therefore,
    # if the queue were empty, then 0-chunks will be generated
    # (0-chunks generate silence when they are played). A 0-chunk is
    # also used to define the structure of the incomming chunks.
    def generate_zero_chunk(self):
        return np.zeros((self.frames_per_chunk, self.number_of_channels), self.sample_type)

    def send(self, data):
        self.sending_sock.sendto(data, (self.destination_address, self.destination_port))

    def receive(self):
        # [Receive an UDP
        # packet](https://docs.python.org/3/library/socket.html#socket.socket.recvfrom).
        # "data" is a new object for each recvfrom() call, containing
        # the payload of the packet. Notice that "data" is a [bytes
        # object](https://docs.python.org/3/library/stdtypes.html#bytes),
        # without any particular structure (it is simply an
        # [inmutable](https://medium.com/@meghamohan/mutable-and-immutable-side-of-python-c2145cf72747)
        # array of bytes). The sender is ignored.
        data, sender = self.receiving_sock.recvfrom(self.MAX_PAYLOAD_BYTES)
        return data
        
    #def unpack
        
    def record_send_play(self, chunk, outdata, frames, time, status):
        # The chunk arg works as record
        # send
        self.send(chunk)
        
        chunk = self.receive()
        # Gives NumPy structure to the chunk.
        chunk = np.frombuffer(chunk, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)
        
        outdata[:] = chunk
        
if __name__ == "__main__":
    intercom = Intercom_minimal()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nIntercom_minimal: goodbye ")
