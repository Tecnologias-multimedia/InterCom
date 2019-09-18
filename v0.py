# No video, no DWT, no compression, no bitplanes, no data-flow
# control, no buffering. Only the transmission of the raw audio data,
# splitted into chunks of fixed length.
#
# https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py


import sounddevice as sd                                                        # https://python-sounddevice.readthedocs.io
import numpy                                                                    # https://numpy.org/
import argparse                                                                 # https://docs.python.org/3/library/argparse.html
import socket                                                                   # https://docs.python.org/3/library/socket.html

if __debug__:
    import sys

class Intercom:

    max_packet_size = 32768                                                     # In bytes
   
    def init(self, args):
        self.bytes_per_sample = args.bytes_per_sample
        self.number_of_channels = args.number_of_channels
        self.samples_per_second = args.samples_per_second
        self.samples_per_chunk = args.samples_per_chunk
        self.packet_format = "!i" + str(self.samples_per_chunk)+"h"             # <chunk_number, chunk_data>
        self.listening_port = args.mlp
        self.destination_IP_addr = args.ia
        self.destination_port = args.ilp

        if __debug__:
            print("bytes_per_sample={}".format(self.bytes_per_sample))
            print("number_of_channels={}".format(self.number_of_channels))
            print("samples_per_second={}".format(self.samples_per_second))
            print("samples_per_chunk={}".format(self.samples_per_chunk))
            print("listening_port={}".format(self.listening_port))

    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)

        def callback(indata, outdata, frames, time, status):
            sending_sock.sendto(
                indata,
                (self.destination_IP_addr, self.destination_port))
            message, source_address = receiving_sock.recvfrom(
                Intercom.max_packet_size)
            outdata[:] = numpy.frombuffer(
                message,
                numpy.int16).reshape(
                    self.samples_per_chunk, self.number_of_channels)

        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=numpy.int16,
                channels=self.number_of_channels,
                callback=callback):
            print('press <Return> to quit')
            input()

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description="Real-time intercom",
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

if __name__ == "__main__":

    intercom = Intercom()
    args = intercom.parse_args()
    intercom.init(args)
    intercom.run()
