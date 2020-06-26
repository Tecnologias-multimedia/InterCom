#
# intercom_minimal.py
#
# A very simple intercom(municator) that sends chunked raw audio data
# (chunks) between two (or more, depending on if the destination
# address is an IP multicast one) networked processes.
#
# The receiver uses a queue for uncoupling the reception of chunks and
# the playback (the chunks of audio can be transmitted with a
# [jitter](https://en.wikipedia.org/wiki/Jitter) different to the
# playing chunk cadence, producing "glitches" during the playback of
# the audio). The number of queued chunks uncontrolled, but small
# (normally 1). Therefore, the delay produced by the queue is very
# small (a chunk time).
#
# Repo: https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py

# Handle command-line arguments. See:
# https://docs.python.org/3/library/argparse.html.
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

# Used for implementing a FIFO queue of chunks of audio. See:
# https://docs.python.org/3/library/queue.html
import queue

# Debug mode modules.
if __debug__:

    # Interface with the OS. See:
    # https://docs.python.org/3/library/sys.html
    import sys

    # Process and system monitoring. See:
    # https://pypi.org/project/psutil/
    try:
        import psutil
    except ModuleNotFoundError:
        import os
        os.system("pip3 install psutil --user")
        import psutil

class Intercom_minimal:

    # Default audio configuration. See: https://nbviewer.jupyter.org/github/vicente-gonzalez-ruiz/YAPT/blob/master/multimedia/sounddevice.ipynb
    
    # 1 = Mono, 2 = Stereo
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
    # limites the maximum length (in bytes) of a chunk of audio.
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
          f"(bytes_per_chunk={self.bytes_per_chunk} > MAX_PAYLOAD_BYTES={Intercom_minimal.MAX_PAYLOAD_BYTES})"

        # Sending and receiving sockets creation and configuration for
        # UDP traffic. See:
        # https://wiki.python.org/moin/UdpCommunication
        self.sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", self.my_port)
        self.receiving_sock.bind(self.listening_endpoint)

        # A queue to store up to 100 chunks.
        self.q = queue.Queue(maxsize=100)

        if __debug__:
            print(f"Intercom_minimal: number_of_channels={self.number_of_channels}")
            print(f"Intercom_minimal: frames_per_second={self.frames_per_second}")
            print(f"Intercom_minimal: frames_per_chunk={self.frames_per_chunk}")
            print(f"Intercom_minimal: samples_per_chunk={self.samples_per_chunk}")
            print(f"Intercom_minimal: my_port={self.my_port}")
            print(f"Intercom_minimal: destination_address={self.destination_address}")
            print(f"Intercom_minimal: destination_port={self.destination_port}")
            print(f"Intercom_minimal: bytes_per_chunk={self.bytes_per_chunk}")
        print("Intercom_minimal: running ...")

    # The audio driver never stops recording and playing. Therefore,
    # if the queue were empty, then 0-chunks will be generated
    # (0-chunks generate silence when they are played).
    def generate_zero_chunk(self):
        return np.zeros((self.frames_per_chunk, self.number_of_channels), self.sample_type)

    # Send a chunk (and possiblely, metadata). The destination is fixed.
    def send(self, payload):
        self.sending_sock.sendto(payload, (self.destination_address, self.destination_port))

    # Receive a chunk.
    def receive(self):
        # [Receive an UDP
        # packet](https://docs.python.org/3/library/socket.html#socket.socket.recvfrom). The
        # socket returns a [bytes
        # structure](https://docs.python.org/3/library/stdtypes.html), an
        # object that exposes the [buffer
        # protocol](https://docs.python.org/3/c-api/buffer.html).
        payload, sender = self.receiving_sock.recvfrom(Intercom_minimal.MAX_PAYLOAD_BYTES)
        return payload

    # The receive_and_buffer() method is running
    # in a infinite loop (see the run() method), and in each iteration
    # receives a chunk of audio and insert it in the tail of the queue
    # of chunks. Notice that recvfrom() is a blocking method.
    def receive_and_buffer(self):
        
        # Gets a chunk. The payload object points to a block of memory
        # containing the payload of the packet. At this moment, Python
        # does not know the structure of such message. Python only
        # knows that there is a block of memory with data. In other
        # words:
        #
        # payload {
        #   [len(payload)] int8 byte;
        # }
        payload = self.receive()

        # Interprets the bytes structure into a NumPy 1-dimensional
        # array of "sample_type" elements. In other words:
        #
        # flat_chunk {
        #   [len(payload)/sizeof(int16)] int16 sample;
        # }
        #
        # See:
        # https://numpy.org/doc/stable/reference/generated/numpy.frombuffer.html
        flat_chunk = np.frombuffer(payload, self.sample_type)

        # Interprets the 1-dimensional array as a 2-dimensional array,
        # in the case that number_of_channels == 2. Therefore:
        #
        # chunk {
        #   [number_of_channels][frames_per_chunk] int16 sample;
        # }
        #
        # Therefore, chunk[0] is the first channel and chunk[1] is the
        # second channel.
        #
        # See:
        # https://numpy.org/doc/stable/reference/generated/numpy.reshape.html
        chunk = flat_chunk.reshape(self.frames_per_chunk, self.number_of_channels)

        # Puts the received chunk on the top of the queue.
        self.q.put(chunk)

    # Shows CPU usage.
    def feedback_message(self):
        sys.stderr.write(str(int(psutil.cpu_percent())) + ' '); sys.stderr.flush()

    # The audio driver provided by sounddevice runs in a
    # [thread](https://en.wikipedia.org/wiki/Thread_(computing))
    # different from the main one. Thus, sounddevice calls the
    # callback function (this function) each time a new chunk of audio
    # is available from the
    # [ADC](https://en.wikipedia.org/wiki/Analog-to-digital_converter). The
    # new chunk is returned in "indata". At the same time, this method
    # allows to send audio chunks stored in "outdata" to the
    # [DAC](https://en.wikipedia.org/wiki/Digital-to-analog_converter). Notice
    # that if the soundcard of the sender and the receiver have been
    # configured with the same parameters (sampling frequency and
    # number of frames per chunk), the cadence of input and output
    # chunks is exactly the same. This condition is a requirement for
    # intercom. See []() for a deeper description of the callback
    # function.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.send(indata)

        try:
            chunk = self.q.get_nowait()
        except queue.Empty:
            chunk = self.generate_zero_chunk()

        # Copy the data of chunk to outdata using slicing. The
        # alternative "outdata = chunk" only copy pointers to objects
        # (there is not data transference between "chunk" and
        # "outdata".
        outdata[:] = chunk

        # Notice that a feedback message is generated each time a
        # chunk is processed.
        if __debug__:
            self.feedback_message()

    # Runs the intercom.
    def run(self):
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=self.record_send_and_play):
            print("¯\_(ツ)_/¯ Press <CTRL> + <c> to quit ¯\_(ツ)_/¯")
            while True:
                self.receive_and_buffer()

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

if __name__ == "__main__":
    intercom = Intercom_minimal()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
