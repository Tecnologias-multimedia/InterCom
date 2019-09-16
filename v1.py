# No video, no DWT, no compression, no data-flow control.
# 
# https://github.com/Tecnologias-multimedia/intercom

import pyaudio                      # http://people.csail.mit.edu/hubert/pyaudio/
import numpy as np                  # https://www.numpy.org
import pywt                         # https://pywavelets.readthedocs.io
#import scipy.stats as st            # https://www.scipy.org/
import argparse                     # https://docs.python.org/3/library/argparse.html
import math                         # https://docs.python.org/3/library/math.html
import multiprocessing              # https://docs.python.org/3/library/multiprocessing.html
import socket                       # https://docs.python.org/3/library/socket.html
import time                         # https://docs.python.org/3/library/time.html
import struct                       # https://docs.python.org/3/library/struct.html

class Intercom:

    max_packet_size = 4096  # In bytes
    
    def __init__(self, bytes_per_sample, number_of_channels, sampling_rate, audio_buffer_size, chunk_size):
        self.bytes_per_sample = bytes_per_sample
        self.number_of_channels = number_of_channels
        self.sampling_rate = sampling_rate
        self.audio_buffer_size = audio_buffer_size
        self.chunk_size = chunk_size
        self.packet_format = "!i" + str(self.chunk_size/8)+"s"                      # <chunk_number, chunk_data>
        
    def send(self, destination_IP_addr, destination_port, number_of_bytes_sent):
        audio = pyaudio.PyAudio()                                      # Create the audio handler.
        stream = audio.open(                                           # Configure the sound card for reading
            format=audio.get_format_from_width(self.bytes_per_sample),
            channels=self.number_of_channels,
            rate=self.sampling_rate,
            input=True,
            frames_per_buffer=self.chunk_size)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)           # Create an UDP socket.
        while True:
            number_of_chunks_sent.value += 1
            _buffer = stream.read(self.chunk_size, exception_on_overflow=False)
            _array = np.frombuffer(_buffer, dtype=np.int16)
            bitplanes = from_array_to_bitplanes(_array)
            for bitplane_number in range(15, -1, -1):
                codestream = self.encode(bitplanes[bitplane_number])
                chunk_number = number_of_chunks_sent.value*15 + (15-bitplane_number)
                message = (chunk_number, bitplane_number, codestream)
                packet = struct.pack(packet_format, *message)
                sock.sendto(packet, (destination_IP_addr, destination_port))       # Send the bitplane.

    def receive(self, listening_port, number_of_received_chunks):
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=audio.get_format_from_width(self.bytes_per_sample),
            channels=self.number_of_channels,
            rate=self.sampling_rate,
            output=True,
            frames_per_buffer=self.chunk_size)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", listening_port)
        sock.bind(listening_endpoint)
        bitplanes = [None]*15
        while True:
            for i in rante(15, -1, -1):
                packet, source_address = sock.recvfrom(Intercom.max_packet_size)
                chunk = struct.unpack(self.packet_format, packet)
                chunk_number, bitplane_number, codestream = chunk[0], chunk[1], chunk[2]
                bitplane = self.decode(codestream)
                bitplanes[bitplane_number] = np.frombuffer(bitplane, dtype=np.int8)
            _buffer = self.from_bitplanes_to_array(bitplanes)
            stream.write(_buffer.tobytes())
            number_of_received_chunks.value += 1

    def from_array_to_bitplanes(self, array):
        bitplanes = []
        for i in range(16):
            bitplanes.append( ((array & (0b1 << i)) >> i).astype(np.int8) )
        return bitplanes

    # <bitplanes> is a list of 16 planes of <self.chunk_size>
    # bits. <bitplanes[0]> (the first bitplane) is a
    # numpy.ndarray. bitplanes[0][0] (the first element of the first
    # bitplane), a numpy.int8. 7 out of 8 bits of bitplanes[0][0] (the
    # 7 more significative) are set always to 0 (therefore, they are
    # "wasted"). This method returns <codestream>, a numpy.ndarray
    # with len(<bitplanes>/8) numpy.uint8 elements with the lowest
    # significant bits of <bitplanes>. In other words, <codestream>
    # compacts the bits of <bitplanes>, avoding the "wasting" of bits
    # in <bitplanes>. The bit of weight 128 (== (1 << 7)), the MSb
    # (Most Significant bit)) of <codestream[0]> = the bit of weight 1
    # of <bitplanes[0], the bit of weight 64 (== (1 << 6)) of
    # <codestream[0]> = the bit of weight 1 of <bitplanes[1], ..., the
    # bit of weight 1 of <codestream[0]> = the bit of weight 1 of
    # <bitplane[7], the bit of weight 128 of <codestream[1]> = the bit
    # of weight 1 of <bitplanes[8]>, etc.
    def encode(self, bitplanes):
        length = int(len(bitplanes)/8)
        codestream = np.zeros((length,), dtype = np.uint8)
        for i in range(0, length):
            codestream[i] = (
                bitplanes[0 + i*8] << 7 |
                bitplanes[1 + i*8] << 6 |
                bitplanes[2 + i*8] << 5 |
                bitplanes[3 + i*8] << 4 |
                bitplanes[4 + i*8] << 3 |
                bitplanes[5 + i*8] << 2 |
                bitplanes[6 + i*8] << 1 |
                bitplanes[7 + i*8] << 0).astype(np.uint64)
        return buffer

    # This methods reverses the <encode> method, generating a list of
    # bitplanes <bitplanes>, decompacting the bits of <codestream>.
    def decode(codestream):
        bitplanes = [
            (codestream & np.uint8(0b1 << 7)) >> 7,
            (codestream & np.uint8(0b1 << 6)) >> 6,
            (codestream & np.uint8(0b1 << 5)) >> 5,
            (codestream & np.uint8(0b1 << 4)) >> 4,
            (codestream & np.uint8(0b1 << 3)) >> 3,
            (codestream & np.uint8(0b1 << 2)) >> 2,
            (codestream & np.uint8(0b1 << 1)) >> 1,
            (codestream & np.uint8(0b1 << 0)) >> 0]
        return bitplanes

def main():
    # Receive parameters for command line, if not, they have default parameters 
    parser = argparse.ArgumentParser(description = "Arguments")
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--chunk_size", help="Samples per chunk.", type=int, default=1024)
    parser.add_argument("-r", "--rate", help="Sampling rate in samples/second.", type=int, default=44100)
    parser.add_argument("-n", "--nchannels", help="Number of channels.", type=int, default=1)
    parser.add_argument("-d", "--depth", help="Depth in bytes of the samples of audio.", type=int, default=2)
    parser.add_argument("-l", "--levels", help="Numbers of levels of the Discrete Wavelet Transform.", type=int, default=5)
    parser.add_argument("-p", "--my_port", help="Listening port.", type=int, default=4444)
    parser.add_argument("-i", "--interlocutor_address", help="Interlocutor's IP address or name.", type=str, default="localhost")
    parser.add_argument("-t", "--interlocutor_port", help="Interlocutor's listening port.", type=int, default=4444)

    args = parser.parse_args()
    # Check if the level of dwt stay in range
    if (args.chunk_size < 2**args.levels):
        print(f"Numbers of levels dwt is not valid. The max levels dwt for chunk size {args.chunk} is {int(math.log(args.chunk,2))}")
        quit()

    # Print input parameters 
    if __debug__:
        print(f"Chunk size: {args.chunk_size}")
        print(f"Sampling rate: {args.rate}")
        print(f"Numbers of channels: {args.nchannels}")
        print(f"Numbers of levels of the DWT: {args.levels}")
        print(f"Sampling depth: {args.depth}")
        print(f"I'm listening at port: {args.my_port}")
        print(f"Interlocutor's port: {args.interlocutor_port}")
        print(f"Interlocutor's address: {args.interlocutor_address}")

    # Shared variables.
    sent_counter = multiprocessing.Value("i", 0)     # Number of chunks of data sent by the sender process.
    received_counter = multiprocessing.Value("i", 0) # Number of chunks of data received by the receiver process.
    max_sent = multiprocessing.Value("i", 0)         # Max sample sent (in absolute value).
    max_received = multiprocessing.Value("i", 0)     # Max sample received (in absolute value).

    receiver_process = multiprocessing.Process(target=receive, args=(args.my_port, args.depth, args.nchannels, args.rate, args.chunk_size, args.levels, received_counter, max_received))
    receiver_process.daemon = True

    sender_process = multiprocessing.Process(target=send, args=(args.interlocutor_address, args.interlocutor_port, args.depth, args.nchannels, args.rate, args.chunk_size, args.levels, sent_counter, max_sent))
    sender_process.daemon = True

    receiver_process.start()
    sender_process.start()

    while True:
        time.sleep(1)
        print(f"Sent {sent_counter.value} chunks, received {received_counter.value} chunks, max_sent={max_sent.value}, max_received={max_received.value}")
        max_sent.value = 0
        max_received.value = 0
    input()

if __name__ == "__main__":
    main()
