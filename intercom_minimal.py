# A very simple intercom(municator) that sends chunked raw audio data
# between two (or more, depending on the destination address)
# networked processes. The receiver uses a queue for uncoupling the
# reception of chunks and the playback. Missing chunks are replaced by
# zeros.
#
# Repo: https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py

import argparse  # https://docs.python.org/3/library/argparse.html
try:
    import sounddevice as sd  # https://python-sounddevice.readthedocs.io
except ModuleNotFoundError:
    import os
    os.system("pip3 install sounddevice --user")
    import sounddevice as sd
try:
    import numpy as np  # https://numpy.org
except ModuleNotFoundError:
    print("Installing numpy with pip")
    import os
    os.system("pip3 install numpy --user")
    import numpy as np
import socket  # https://docs.python.org/3/library/socket.html
import queue  # https://docs.python.org/3/library/queue.html

if __debug__:
    import sys
    try:
        import psutil
    except ModuleNotFoundError:
        import os
        os.system("pip3 install psutil --user")
        import psutil

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
    # if the queue of chunks is empty, then zero chunks are generated
    # 0-chunks generate silence when they are played.
    def generate_zero_chunk(self):
        cell = np.zeros((self.frames_per_chunk, self.number_of_channels), self.precision_type)
        #cell = np.zeros((self.frames_per_chunk, self.number_of_channels), np.int32)
        #print("intercom: self.frames_per_chunk={} self.number_of_channels={} self.precision_type={}".format(self.frames_per_chunk, self.number_of_channels, self.precision_type))
        return cell

    def send(self, message):
        self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    def receive(self):
        return self.receiving_sock.recvfrom(Intercom_minimal.MAX_MESSAGE_BYTES)

    # The audio driver runs two different threads, and this is one of
    # them. The receive_and_buffer() method is running in a infinite
    # loop (see the run() method), and in each iteration receives a
    # chunk of audio and insert it in the tail of the queue of
    # chunks. Notice that recvfrom() is a blocking method.
    def receive_and_buffer(self):
        message, source_address = self.receive() #self.receiving_sock.recvfrom(Intercom_minimal.MAX_MESSAGE_BYTES)
        chunk = np.frombuffer(message, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)
        self.q.put(chunk)

    def feedback_message(self):
        sys.stderr.write(str(int(psutil.cpu_percent())) + ' '); sys.stderr.flush()

    # This is the second method that the audio driver runs in a
    # thread. The record_send_and_play() method is called each time a
    # new chunk of audio is available, so, it records audio (returned
    # in "indata"). This method also allows to play chunks of audio
    # (stored in "outdata"). "frames" is the number of frames per
    # chunk. "time" and "status" are ignored.
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.send(indata)
        #self.sending_sock.sendto(indata, (self.destination_address, self.destination_port))
        try:
            chunk = self.q.get_nowait()
        except queue.Empty:
            chunk = self.generate_zero_chunk()
        outdata[:] = chunk
        if __debug__:
            self.feedback_message()

    # Runs intercom. 
    def run(self):
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=self.record_send_and_play):
            print("¯\_(ツ)_/¯ Press <CTRL> + <c> to quit ¯\_(ツ)_/¯")
            while True:
                self.receive_and_buffer()

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
