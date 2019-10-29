# No video, no DWT, no compression, no bitplanes, no data-flow
# control, no buffering. Only the transmission of the raw audio data,
# splitted into chunks of fixed length.
#
# https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py

import sounddevice as sd                                                        # https://python-sounddevice.readthedocs.io
import numpy as np                                                              # https://numpy.org/
import argparse                                                                 # https://docs.python.org/3/library/argparse.html
import socket                                                                   # https://docs.python.org/3/library/socket.html
import queue                                                                    # https://docs.python.org/3/library/queue.html

if __debug__:
    import sys

class Intercom:

    MAX_MESSAGE_SIZE = 32768                                                    # In bytes

    def init(self, args):
        self.number_of_channels = args.number_of_channels
        self.frames_per_second = args.frames_per_second
        self.frames_per_chunk = args.frames_per_chunk
        self.listening_port = args.mlp
        self.destination_IP_addr = args.ia
        self.destination_port = args.ilp
        self.bytes_per_chunk = self.frames_per_chunk * self.number_of_channels * np.dtype(np.int16).itemsize
        self.samples_per_chunk = self.frames_per_chunk * self.number_of_channels
        self.sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", self.listening_port)
        self.receiving_sock.bind(self.listening_endpoint)
        self.q = queue.Queue(maxsize=100000)

        if __debug__:
            print(f"number_of_channels={self.number_of_channels}")
            print(f"frames_per_second={self.frames_per_second}")
            print(f"frames_per_chunk={self.frames_per_chunk}")
            print(f"samples_per_chunk={self.samples_per_chunk}")
            print(f"listening_port={self.listening_port}")
            print(f"destination_IP_address={self.destination_IP_addr}")
            print(f"destination_port={self.destination_port}")
            print(f"bytes_per_chunk={self.bytes_per_chunk}")

    def generate_zero_chunk(self):
        return np.zeros((self.frames_per_chunk, self.number_of_channels), np.int16)
    def receive_and_buffer(self):
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        chunk = np.frombuffer(message, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)
        self.q.put(chunk)
        
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.sending_sock.sendto(indata, (self.destination_IP_addr, self.destination_port))
        try:
            chunk = self.q.get_nowait()
        except queue.Empty:
            chunk = self.generate_zero_chunk()
        outdata[:] = chunk
        if __debug__:
            sys.stderr.write("."); sys.stderr.flush()
            
    def run(self):
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=self.record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            while True:
                self.receive_and_buffer()

    def add_args(self):
        parser = argparse.ArgumentParser(description="Real-time intercom", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-s", "--frames_per_chunk", help="Samples per chunk.", type=int, default=1024)
        parser.add_argument("-r", "--frames_per_second", help="Sampling rate in frames/second.", type=int, default=44100)
        parser.add_argument("-c", "--number_of_channels", help="Number of channels.", type=int, default=2)
        parser.add_argument("-p", "--mlp", help="My listening port.", type=int, default=4444)
        parser.add_argument("-i", "--ilp", help="Interlocutor's listening port.", type=int, default=4444)
        parser.add_argument("-a", "--ia", help="Interlocutor's IP address or name.", type=str, default="localhost")
        return parser

if __name__ == "__main__":
    intercom = Intercom()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
