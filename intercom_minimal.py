#
# Intercom_minimal..py
#
# A very simple intercom(municator) that sends chunked raw audio data
# (audio blocks, which we simply call "chunks") between two (or more,
# depending on if the destination address is an IP multicast one)
# networked processes.
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
#
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

# Process and system monitoring. See:
# https://pypi.org/project/psutil/
try:
    import psutil
except ModuleNotFoundError:
    import os
    os.system("pip3 install psutil --user")
    import psutil

# Accumulated CPU usage.
CPU_total = 0

# Number of samples of CPU usage (used for computing an average).
CPU_samples = 0

import sys # Quitar

class Intercom_minimal:

    NUMBER_OF_CHANNELS = 2
    FRAMES_PER_SECOND = 44100
    FRAMES_PER_CHUNK = 1024
    MAX_MESSAGE_BYTES = 32768
    MY_PORT = 4444
    DESTINATION_PORT = 4444
    DESTINATION_ADDRESS = "localhost"

    def init(self, args):
        self.number_of_channels = args.number_of_channels
        self.frames_per_second = args.frames_per_second
        self.frames_per_chunk = args.frames_per_chunk
        self.my_port = args.my_port
        self.destination_address = args.destination_address 
        self.destination_port = args.destination_port
        self.bytes_per_chunk = self.frames_per_chunk * self.number_of_channels * np.dtype(np.int16).itemsize
        self.samples_per_chunk = self.frames_per_chunk * self.number_of_channels
        self.sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", self.my_port)
        self.receiving_sock.bind(self.listening_endpoint)
        self.q = queue.Queue(maxsize=100000)
        self.precision_type = np.int16

        if __debug__:
            print(f"intercom: number_of_channels={self.number_of_channels}")
            print(f"intercom: frames_per_second={self.frames_per_second}")
            print(f"intercom: frames_per_chunk={self.frames_per_chunk}")
            print(f"intercom: samples_per_chunk={self.samples_per_chunk}")
            print(f"intercom: my_port={self.my_port}")
            print(f"intercom: destination_address={self.destination_address}")
            print(f"intercom: destination_port={self.destination_port}")
            print(f"intercom: bytes_per_chunk={self.bytes_per_chunk}")
        print("intercom: intercom-unicating")

    # The audio driver never stops recording and playing. Therefore,
    # if the queue of chunks is empty, then zero chunks are generated
    # in order to produce a silence at the receiver.
    def generate_zero_chunk(self):
        cell = np.zeros((self.frames_per_chunk, self.number_of_channels), self.precision_type)
        #cell = np.zeros((self.frames_per_chunk, self.number_of_channels), np.int32)
        #print("intercom: self.frames_per_chunk={} self.number_of_channels={} self.precision_type={}".format(self.frames_per_chunk, self.number_of_channels, self.precision_type))
        return cell

    def send_message(self, message):
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    def receive_message(self):
        return self.receiving_sock.recvfrom(Intercom_minimal.MAX_MESSAGE_BYTES)

    # The audio driver runs two different threads, and this is one of
    # them. The receive_and_buffer() method is running in a infinite
    # loop (see the run() method), and in each iteration receives a
    # chunk of audio and insert it in the tail of the queue of
    # chunks. Notice that recvfrom() is a blocking method.
    def receive_and_buffer(self):
        message, source_address = self.receive_message() #self.receiving_sock.recvfrom(Intercom_minimal.MAX_MESSAGE_BYTES)
        chunk = np.frombuffer(message, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)
        self.q.put(chunk)

    # This is the second method that the audio driver runs in a
    # thread. The record_send_and_play() method is called each time a
    # new chunk of audio is available, so, it records audio (returned
    # in "indata"). This method also allows to play chunks of audio
    # (stored in "outdata"). "frames" is the number of frames per
    # chunk. "time" and "status" are ignored.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.send_message(indata)
        #self.sending_sock.sendto(indata, (self.destination_address, self.destination_port))
        try:
            chunk = self.q.get_nowait()
        except queue.Empty:
            chunk = self.generate_zero_chunk()
        outdata[:] = chunk
        if __debug__:
            sys.stderr.write("."); sys.stderr.flush()

    # Runs Intercom_minimal. 
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
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nIntercom_minimal: goodbye ¯\_(ツ)_/¯")
        print("Intercom_minimal: average CPU usage =", CPU_total/CPU_samples, "%")

