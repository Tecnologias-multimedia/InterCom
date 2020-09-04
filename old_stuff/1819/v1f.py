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
            print("bytes_per_sample={}".format(self.bytes_per_sample))
            print("number_of_channels={}".format(self.number_of_channels))
            print("samples_per_second={}".format(self.samples_per_second))
            print("samples_per_chunk={}".format(self.samples_per_chunk))

    def send(self, destination_IP_addr, destination_port, number_of_chunks_sent):

        if __debug__:
            print("send: destination_IP_addr={}, destination_port={}".
                  format(destination_IP_addr, destination_port))

        # UDP socket to send
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        def record_callback(indata, frames, time, status):
            print(indata[0])
            sock.sendto(indata, (destination_IP_addr, destination_port))
            number_of_chunks_sent.value += 1

        stream = sd.InputStream(
            blocksize=self.samples_per_chunk,
            device=None,
            channels=self.number_of_channels,
            samplerate=self.samples_per_second,
            dtype=numpy.int16,
            callback=record_callback)
        with stream:
            while True:
                time.sleep(1)
                print("O")

    def receive(self, listening_port, number_of_chunks_received):

        if __debug__:
            print("receive: listening_port={}".format(listening_port))

        # UDP socket to receive
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", listening_port)
        self.sock.bind(listening_endpoint)

        def play_callback(outdata, frames, time, status):
            message, source_address = self.sock.recvfrom(Intercom.max_packet_size)
            outdata = numpy.frombuffer(message, numpy.int16).reshape(self.samples_per_chunk, self.number_of_channels)
            print("->", outdata[0])
            number_of_chunks_received.value += 1

        with sd.OutputStream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                device=None,
                channels=self.number_of_channels,
                dtype=numpy.int16,
                callback=play_callback):

            while True:
                time.sleep(1)
                print("o")
        while True:
            callback(None, None, None, None)

#        with sd.RawOutputStream(
#                samplerate=self.samples_per_second,
#                blocksize=self.samples_per_chunk,
#                device=None,
#                channels=self.number_of_channels,
#                callback=callback):

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
            print("Samples per chunk: {}".format(self.args.samples_per_chunk))
            print("Samples per second: {}".format(self.args.samples_per_second))
            print("Numbers of channels: {}".format(self.args.number_of_channels))
            print("Bytes per sample: {}".format(self.args.bytes_per_sample))
            print("I'm listening at port: {}".format(self.args.mlp))
            print("Interlocutor's listening port: {}".format(self.args.ilp))
            print("Interlocutor's IP address: {}".format(self.args.ia))

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
            print("Sent {}, received {} chunks".
                  format(number_of_chunks_sent.value, number_of_chunks_received.value))

if __name__ == "__main__":

    intercom = Intercom()
    args = intercom.parse_args()
    intercom.init(args)
    intercom.run()
