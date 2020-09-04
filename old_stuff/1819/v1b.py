# No video, no DWT, no compression, no bitplanes, no data-flow
# control. Only the transmission of the raw audio data, splitted into
# chunks.
# 
# https://github.com/Tecnologias-multimedia/intercom

import sounddevice as sd            # https://python-sounddevice.readthedocs.io
import numpy
import argparse                     # https://docs.python.org/3/library/argparse.html
import multiprocessing              # https://docs.python.org/3/library/multiprocessing.html
import socket                       # https://docs.python.org/3/library/socket.html
import time                         # https://docs.python.org/3/library/time.html

if __debug__:
    import sys

class Intercom:

    max_packet_size = 32768  # In bytes
    
    def init(self, args):
        self.bytes_per_sample = args.bytes_per_sample
        self.number_of_channels = args.number_of_channels
        self.samples_per_second = args.samples_per_second
        self.samples_per_chunk = args.samples_per_chunk
        self.packet_format = "!i" + str(self.samples_per_chunk)+"h"             # <chunk_number, chunk_data>

        if __debug__:
            print(f"bytes_per_sample={self.bytes_per_sample}")
            print(f"number_of_channels={self.number_of_channels}")
            print(f"samples_per_second={self.samples_per_second}")
            print(f"samples_per_chunk={self.samples_per_chunk}")

    def send(self, destination_IP_addr, destination_port, number_of_chunks_sent):

        if __debug__:
            print(f"send: destination_IP_addr={destination_IP_addr}, \
destination_port={destination_port}")

        # UDP socket to send
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        def callback(indata):
            sock.sendto(indata, (destination_IP_addr, destination_port))
            number_of_chunks_sent.value += 1

        while True:
            callback(bytes(1024))
            time.sleep(1)

    def receive(self, listening_port, number_of_chunks_received):

        if __debug__:
            print(f"receive: listening_port={listening_port}")

        # UDP socket to receive
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", listening_port)
        self.sock.bind(listening_endpoint)

        def callback(outdata):
            outdata, source_address = self.sock.recvfrom(Intercom.max_packet_size)
            number_of_chunks_received.value += 1

        while True:
            callback(None)

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description = "Real-time intercom",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-s",
                            "--samples_per_chunk",
                            help="Samples per chunk.",
                            type=int,
                            default=1024)
        parser.add_argument("-r",
                            "--samples_per_second",
                            help="Sampling rate in samples/second.",
                            type=int,
                            default=44100)
        parser.add_argument("-c",
                            "--number_of_channels",
                            help="Number of channels.",
                            type=int,
                            default=2)
        parser.add_argument("-b",
                            "--bytes_per_sample",
                            help="Depth in bytes of the samples of audio.",
                            type=int,
                            default=2)
        parser.add_argument("-p",
                            "--mlp",
                            help="My listening port.",
                            type=int,
                            default=4444)
        parser.add_argument("-i",
                            "--ilp",
                            help="Interlocutor's listening port.",
                            type=int,
                            default=4444)
        parser.add_argument("-a",
                            "--ia",
                            help="Interlocutor's IP address or name.",
                            type=str,
                            default="localhost")

        args = parser.parse_args()
        return args

        # Print input parameters
        if __debug__:
            print(f"Samples per chunk: {self.args.samples_per_chunk}")
            print(f"Samples per second: {self.args.samples_per_second}")
            print(f"Numbers of channels: {self.args.number_of_channels}")
            print(f"Bytes per sample: {self.args.bytes_per_sample}")
            print(f"I'm listening at port: {self.args.mlp}")
            print(f"Interlocutor's listening port: {self.args.ilp}")
            print(f"Interlocutor's IP address: {self.args.ia}")

    def instance(self):
        self.intercom = Intercom(
            bytes_per_sample = args.bytes_per_sample,
            number_of_channels = args.number_of_channels,
            samping_rate = args.samples_per_second,
            samples_per_chunk = args.samples_per_chunk
        )

    def run(self):
        # Shared variables
        number_of_chunks_sent = multiprocessing.Value("i", 0)
        number_of_chunks_received = multiprocessing.Value("i", 0)

        # Running processes
        sender_process = multiprocessing.Process(
            target=self.send,
            args=(
                args.ia,
                args.ilp,
                number_of_chunks_sent))
        sender_process.daemon = True
        receiver_process = multiprocessing.Process(
            target=self.receive,
            args=(
                args.mlp,
                number_of_chunks_received))
        receiver_process.daemon = True
        receiver_process.start()
        sender_process.start()

        while True:
            time.sleep(1)
            print(f"Sent {number_of_chunks_sent.value}, received {number_of_chunks_received.value} chunks")

if __name__ == "__main__":

    intercom = Intercom()
    args = intercom.parse_args()
    intercom.init(args)
    intercom.run()
