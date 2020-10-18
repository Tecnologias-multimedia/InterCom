#
# Minimal Intercom
#
# A very simple inercomunicator based in Intercom_minimal.py and wire.py
# programs that sends chunk audio in blocks between two (or one) networked
# processes, based in peer to peer p2p architecture. Both parts are sender
# and receiver simultaneously
#
# The callback method based system (with numpy arrays) will be used to
# record and play audio. In order to control lantency issues, fixed chunks
# will be used. The chunks of audio recorder are send using a UDP socket.
# The receiver will have all chunk received stored in the socket queue instead
# of using an explicit queue object. It means the callback method has to
# send the current recorded chunk and withdraw an element of the socket queue.
# There is no control of the receiver socket queue.

# Package to handle command-line arguments
import argparse

# Package to use socket API for network communication
import socket

# Package that provides bindings for PortAudio library
# that allows usage of numpy arrays.
try:
    import sounddevice as sd
except ModuleNotFoundError:
    import os
    os.system("pip3 install sounddevice --user")
    import sounddevice as sd

# Package that provides efficient arrays.
try:
    import numpy as np
except ModuleNotFoundError:
    print("Installing numpy with pip")
    import os
    os.system("pip3 install numpy --user")
    import numpy as np

# Package to process and system monitoring
try:
    import psutil
except ModuleNotFoundError:
    import os
    os.system("pip3 install psutil --user")
    import psutil

# Accumulated CPU usage
CPU_total = 0

# Number of samples of CPU
CPU_samples = 0

# MinimalIntercom class

class MinimalIntercom:
    """
    Class to wrap Minimal Intercom functionalities and data

    Attributes
    ----------

    NUMBER_CHANNELS (int) (static): Number of channels by default

    SAMPLE_RATE (int) (static): Sampling frequency. Number of frames per second

    CHUNK_SIZE (int) (static): Size of sampling chunk. A chunk is composed
    by frames

    SOURCE_PORT (int) (static): Port used to receive data from network

    DESTINATION_PORT (int) (static): Port used to send data to networks

    DESTINATION_ADDRESS (string) (static): IP address of destination computer

    MAX_PAYLOAD_BYTES (int) (static): Maximum size of UDP payload


    """
    # Number of channels by default
    NUMBER_CHANNELS = 1

    # Sampling frequency. Number of frames per second
    SAMPLE_RATE = 44100

    # Size of sampling chunk. A chunk is composed by frames
    CHUNK_SIZE = 512

    # Port used to receive data from network
    SOURCE_PORT = 7676

    # Port used to send data to networks
    DESTINATION_PORT = 7676

    # IP address of destination computer
    DESTINATION_ADDRESS = "localhost" # "192.168.1.37"

    #  Maximum size of UDP payload
    MAX_PAYLOAD_BYTES = 32768

    def __init__(self, args):
        """
        Class constructor

        The constructor class requires several arguments that must be provided before
        to get an intercom instance. The constructor also creates the sockets required
        to send and receive data. In order to acquire the arguments correctly, there
        is an static method called add_args.
        """

        # Elemental instance variables initialized by arguments
        self.number_of_channels = args.number_of_channels
        self.sample_rate = args.frames_per_second
        self.chunk_size = args.frames_per_chunk
        self.source_port = args.source_port
        self.destination_address = args.destination_address
        self.destination_port = args.destination_port

        # Stream parameters for numpy type
        self.sample_type = np.int16

        # Generated attributes using elemental instance varaibles
        self.samples_per_chunk = self.chunk_size * self.number_of_channels
        self.bytes_per_chunk = self.samples_per_chunk * np.dtype(self.sample_type).itemsize

        # Assertion is activated if number of bytes per chunk is less than maximum payload size
        # This action is used to ensure reliable UDP communication
        assert self.bytes_per_chunk <= MinimalIntercom.MAX_PAYLOAD_BYTES, \
        f"bytes_per_chunk={self.bytes_per_chunk} > MAX_PAYLOAD_BYTES={MinimalIntercom.MAX_PAYLOAD_BYTES}h"

        # Endpoints pair declaration
        self.sender_endpoint = (self.destination_address, self.destination_port)
        self.receiver_endpoint = ("0.0.0.0", self.source_port)

        # Socket initialization
        self.sender_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.receiver_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Set receiver socket in non bloking
        self.receiver_socket.setblocking(0)

        # Bind listener socket
        self.receiver_socket.bind(self.receiver_endpoint)

        # Auxiliary chunk filled width zeros
        self.zero_chunk = self.generate_zero_chunk()

        # Data received via socket. Initialized with zero values
        self.data = self.generate_zero_chunk()

    # Destructor of class
    def __del__(self):
        """ Destructor of class. Just closes socket before to destroy it """
        self.receiver_socket.close()

    def to_print(self):
        """To print instance variables"""

        print(f"Minimal intercom: number_of_channels={self.number_of_channels}")
        print(f"Minimal intercom: sample rate={self.sample_rate}")
        print(f"Minimal intercom: chunk_size={self.chunk_size}")
        print(f"Minimal intercom: samples_per_chunk={self.samples_per_chunk}")
        print(f"Minimal intercom: source port={self.source_port}")
        print(f"Minimal intercom: destination_address={self.destination_address}")
        print(f"Minimal intercom: destination_port={self.destination_port}")
        print(f"Minimal intercom: bytes_per_chunk={self.bytes_per_chunk}")

    # Zero chunk generator
    def generate_zero_chunk(self):
        """ Generator of numpy chunk filled with zeros

        Returns
        ------
        numpy array filled with zeros
        """
        return np.zeros((self.chunk_size, self.number_of_channels), self.sample_type)

    def send(self, data):
        """ Send data over sender socket

        Parameters
        _________
        data
            Data to send over UDP socket. A numpy array is expected
        """
        self.sender_socket.sendto(data, self.sender_endpoint)  #self.sender_endpoint)

    def receive(self):
        """Receive data from receiver socket

        Raises
        ______
        Resource temporarily unavailable
            Socket may be empty. In non-blocking UDP socket an exception
            of this type is raised.
        """

        # Data is required from socket. Howvere, socket may have no data, so to hadle
        # this situation, try-catch block is required
        try:
            # Store received data in local variable
            data, status = self.receiver_socket.recvfrom(self.bytes_per_chunk)

            # Due to data is byte object, conversion to numpy array is required
            data = np.frombuffer(data, self.sample_type).reshape(self.chunk_size, self.number_of_channels)
        except Exception as e:
            print("Exception: ", e)
            # Id there is no data in socket, get zero filled chunk
            data = self.generate_zero_chunk()

        # Return data
        return data

    def feedback(self):
        global CPU_total
        global CPU_samples
        CPU_usage = psutil.cpu_percent()  # User (not intercom) time
        CPU_total += CPU_usage
        CPU_samples += 1
        print(f"{int(CPU_usage)}", flush=True, end=' ')

    # Callback method required from non blocking Sounddevice audio stream
    def callback(self, indata, outdata, frames, time, status):
        """Callback method

        In non blocking audio stream, a new thread is created
        and periodically executes the callback method. Usually
        the call occurs when new input data (indata) is available to
        manipulate. Is recommended to manage output stream in the callback
        method also

        Note: This method has the implementation of the algorithm
        proposed in milestone 5 in Multimedia Technology subject

        The arguments are imposed to Sounndevice callback signature
        """

        # Send data via sender socket
        self.send(indata)

        # Receive data via receiver socket
        self.data = self.receive()

        outdata[:] = self.data

        self.feedback()


    def start(self):
        with sd.Stream(samplerate=self.sample_rate, blocksize=self.chunk_size, dtype=self.sample_type,
                       channels=self.number_of_channels, callback=self.callback):
            input()

    @staticmethod
    def add_args():
        parser = argparse.ArgumentParser(description = "Real-Time Audio Intercommunicator",
                                        formatter_class = argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-s", "--frames_per_chunk",
                            help="Number of frames (stereo samples) per chunk.",
                            type=int, default=MinimalIntercom.CHUNK_SIZE)
        parser.add_argument("-r", "--frames_per_second",
                            help="Sampling rate in frames/second.",
                            type=int, default=MinimalIntercom.SAMPLE_RATE)
        parser.add_argument("-c", "--number_of_channels",
                            help="Number of channels.",
                            type=int, default=MinimalIntercom.NUMBER_CHANNELS)
        parser.add_argument("-p", "--source_port",
                            help="My listening port.",
                            type=int, default=MinimalIntercom.SOURCE_PORT)
        parser.add_argument("-i", "--destination_port",
                            help="Interlocutor's listening port.",
                            type=int, default=MinimalIntercom.DESTINATION_PORT)
        parser.add_argument("-a", "--destination_address",
                            help="Interlocutor's IP address or name.",
                            type=str, default=MinimalIntercom.DESTINATION_ADDRESS)
        return parser

# MAIN

if __name__ == "__main__":
    parser_arguments = MinimalIntercom.add_args()
    args = parser_arguments.parse_args()
    # print(args)
    intercom = MinimalIntercom(args)
    intercom.to_print()
    try:
        intercom.start()
    except KeyboardInterrupt:
        parser_arguments.exit(1,"\n Interrupted by user")
    except Exception as e:
        parser_arguments.exit(1, type(e).__name__ + ': ' + str(e))


