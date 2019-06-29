# intercom.py
# https://github.com/Tecnologias-multimedia/intercom
#
# P2P real-time audio/video sender and receiver.

import pyaudio                      # http://people.csail.mit.edu/hubert/pyaudio/
import numpy as np                  # https://www.numpy.org
import pywt                         # https://pywavelets.readthedocs.io
#import scipy.stats as st            # https://www.scipy.org/
import argparse                     # https://docs.python.org/3/library/argparse.html
import math                         # https://docs.python.org/3/library/math.html
import multiprocessing              # https://docs.python.org/3/library/multiprocessing.html
import socket                       # https://docs.python.org/3/library/socket.html
import time                         # https://docs.python.org/3/library/time.html

# INPUT: A list of subbands of coefficiets. subbands: [], subbands[0]: numpy.ndarray, subbands[0][0]: numpy.float64.
# OUTPUT: Returns a list of 32 "bitplanes". bitplanes: [], bp[0]: numpy.ndarray, bp[0][0]: numpy.int8.
def create_bitplanes(subbands):
    a = np.concatenate(subbands, axis=0)                   # Join all subbands in a single array. a: numpy.ndarray, a[0]: numpy.float64.
    b = a.astype(np.int32)                                 # Converts all coefficiets into int32. b: numpy.ndarray, b[0]: numpy.int32.
    bitplanes = [((b & (0b1<<31)) >> 31).astype(np.int8),  # Split the coeffs into bitplanes.
                 ((b & (0b1<<30)) >> 30).astype(np.int8),
                 ((b & (0b1<<29)) >> 29).astype(np.int8),
                 ((b & (0b1<<28)) >> 28).astype(np.int8),
                 ((b & (0b1<<27)) >> 27).astype(np.int8),
                 ((b & (0b1<<26)) >> 26).astype(np.int8),
                 ((b & (0b1<<25)) >> 25).astype(np.int8),
                 ((b & (0b1<<24)) >> 24).astype(np.int8),
                 ((b & (0b1<<23)) >> 23).astype(np.int8),
                 ((b & (0b1<<22)) >> 22).astype(np.int8),
                 ((b & (0b1<<21)) >> 21).astype(np.int8),
                 ((b & (0b1<<20)) >> 20).astype(np.int8),
                 ((b & (0b1<<19)) >> 19).astype(np.int8),
                 ((b & (0b1<<18)) >> 18).astype(np.int8),
                 ((b & (0b1<<17)) >> 17).astype(np.int8),
                 ((b & (0b1<<16)) >> 16).astype(np.int8),
                 ((b & (0b1<<15)) >> 15).astype(np.int8),
                 ((b & (0b1<<14)) >> 14).astype(np.int8),
                 ((b & (0b1<<13)) >> 13).astype(np.int8),
                 ((b & (0b1<<12)) >> 12).astype(np.int8),
                 ((b & (0b1<<11)) >> 11).astype(np.int8),
                 ((b & (0b1<<10)) >> 10).astype(np.int8),
                 ((b & (0b1<< 9)) >>  9).astype(np.int8),
                 ((b & (0b1<< 8)) >>  8).astype(np.int8),
                 ((b & (0b1<< 7)) >>  7).astype(np.int8),
                 ((b & (0b1<< 6)) >>  6).astype(np.int8),
                 ((b & (0b1<< 5)) >>  5).astype(np.int8),
                 ((b & (0b1<< 4)) >>  4).astype(np.int8),
                 ((b & (0b1<< 3)) >>  3).astype(np.int8),
                 ((b & (0b1<< 2)) >>  2).astype(np.int8),
                 ((b & (0b1<< 1)) >>  1).astype(np.int8),
                 ( b &  0b1)            .astype(np.int8)]
    return bitplanes

# INPUT: A list of 32 "bitplanes". bitplanes: [], bp[0]: numpy.ndarray, bp[0][0]: numpy.int8.
# OUTPUT: Returns a list of subbands of coefficiets. subbands: [], subbands[0]: numpy.ndarray, subbands[0][0]: numpy.float64.
def create_subbands(bitplanes, dwt_levels):
    a = (bitplanes[31] << 31 |    # Join all bitplanes in a single array. a: numpy.ndarray, a[0]: numpy.float64.
         bitplanes[30] << 30 |
         bitplanes[29] << 29 |
         bitplanes[28] << 28 |
         bitplanes[27] << 27 |
         bitplanes[26] << 26 |
         bitplanes[25] << 25 | 
         bitplanes[24] << 24 |
         bitplanes[23] << 23 |
         bitplanes[22] << 22 |
         bitplanes[21] << 21 |
         bitplanes[20] << 20 |
         bitplanes[19] << 19 |
         bitplanes[18] << 18 | 
         bitplanes[17] << 17 |
         bitplanes[16] << 16 |
         bitplanes[15] << 15 |
         bitplanes[14] << 14 |
         bitplanes[13] << 13 |
         bitplanes[12] << 12 |
         bitplanes[11] << 11 |
         bitplanes[10] << 10 |
         bitplanes[ 9] <<  9 |
         bitplanes[ 8] <<  8 |
         bitplanes[ 7] <<  7 |
         bitplanes[ 6] <<  6 |
         bitplanes[ 5] <<  5 |
         bitplanes[ 4] <<  4 |
         bitplanes[ 3] <<  3 |
         bitplanes[ 2] <<  2 |
         bitplanes[ 1] <<  1 |
         bitplanes[ 0]).astype(np.int32).astype(float)
    # Now, create the subbands splitting this array.
    subbands = []
    buf = []
    jumps = [0]*(dwt_levels+1)
    for z in range(0, dwt_levels+1):
        jumps[z] = 2**(int(math.log(len(a),2))-(dwt_levels-z))-1
    count = 0
    for x in range(0, len(a)):
        buf.append(a[x])
        if (x == jumps[count]):
            subbands.append(np.array(buf))
            buf = []
            count += 1
    return subbands

def encode(plane):
    # Recive plano a plano (del 31 al 0)
    length = int(len(plane)/64)
    buffer = np.zeros((length,), dtype = np.uint64)
    inicio = 0
    fin = 0
    for i in range(0, length):
        fin += 64
        buffer[i] = (plane[0+inicio]<<63 | plane[1+inicio]<<62 | plane[2+inicio]<<61 | plane[3+inicio]<<60
            | plane[4+inicio]<<59 | plane[5+inicio]<<58 | plane[6+inicio]<<57 | plane[7+inicio]<<56
            | plane[8+inicio]<<55 | plane[9+inicio]<<54 | plane[10+inicio]<<53 | plane[11+inicio]<<52
            | plane[12+inicio]<<51 | plane[13+inicio]<<50 | plane[14+inicio]<<49 | plane[15+inicio]<<48
            | plane[16+inicio]<<47 | plane[17+inicio]<<46 | plane[18+inicio]<<45 | plane[19+inicio]<<44
            | plane[20+inicio]<<43 | plane[21+inicio]<<42 | plane[22+inicio]<<41 | plane[23+inicio]<<40
            | plane[24+inicio]<<39 | plane[25+inicio]<<38 | plane[26+inicio]<<37 | plane[27+inicio]<<36
            | plane[28+inicio]<<35 | plane[29+inicio]<<34 | plane[30+inicio]<<33 | plane[31+inicio]<<32
            | plane[32+inicio]<<31 | plane[33+inicio]<<30 | plane[34+inicio]<<29 | plane[35+inicio]<<28
            | plane[36+inicio]<<27 | plane[37+inicio]<<26 | plane[38+inicio]<<25 | plane[39+inicio]<<24
            | plane[40+inicio]<<23 | plane[41+inicio]<<22 | plane[42+inicio]<<21 | plane[43+inicio]<<20
            | plane[44+inicio]<<19 | plane[45+inicio]<<18 | plane[46+inicio]<<17 | plane[47+inicio]<<16
            | plane[48+inicio]<<15 | plane[49+inicio]<<14 | plane[50+inicio]<<13 | plane[51+inicio]<<12
            | plane[52+inicio]<<11 | plane[53+inicio]<<10 | plane[54+inicio]<<9 | plane[55+inicio]<<8
            | plane[56+inicio]<<7 | plane[57+inicio]<<6 | plane[58+inicio]<<5 | plane[59+inicio]<<4
            | plane[60+inicio]<<3 | plane[61+inicio]<<2 | plane[62+inicio]<<1 | plane[63+inicio]<<0).astype(np.uint64)
        inicio = fin
    return buffer

def decode(plane):
    a = [(plane & np.uint64(0b1<<63)) >> 63,(plane & np.uint64(0b1<<62)) >> 62, (plane & np.uint64(0b1<<61)) >> 61, (plane & np.uint64(0b1<<60)) >> 60
        , (plane & np.uint64(0b1<<59)) >> 59, (plane & np.uint64(0b1<<58)) >> 58, (plane & np.uint64(0b1<<57)) >> 57, (plane & np.uint64(0b1<<56)) >> 56
        , (plane & np.uint64(0b1<<55)) >> 55, (plane & np.uint64(0b1<<54)) >> 54, (plane & np.uint64(0b1<<53)) >> 53, (plane & np.uint64(0b1<<52)) >> 52
        , (plane & np.uint64(0b1<<51)) >> 51, (plane & np.uint64(0b1<<50)) >> 50, (plane & np.uint64(0b1<<49)) >> 49, (plane & np.uint64(0b1<<48)) >> 48
        , (plane & np.uint64(0b1<<47)) >> 47, (plane & np.uint64(0b1<<46)) >> 46, (plane & np.uint64(0b1<<45)) >> 45, (plane & np.uint64(0b1<<44)) >> 44
        , (plane & np.uint64(0b1<<43)) >> 43, (plane & np.uint64(0b1<<42)) >> 42, (plane & np.uint64(0b1<<41)) >> 41, (plane & np.uint64(0b1<<40)) >> 40
        , (plane & np.uint64(0b1<<39)) >> 39, (plane & np.uint64(0b1<<38)) >> 38, (plane & np.uint64(0b1<<37)) >> 37, (plane & np.uint64(0b1<<36)) >> 36
        , (plane & np.uint64(0b1<<35)) >> 35, (plane & np.uint64(0b1<<34)) >> 34, (plane & np.uint64(0b1<<33)) >> 33, (plane & np.uint64(0b1<<32)) >> 32
        , (plane & np.uint64(0b1<<31)) >> 31, (plane & np.uint64(0b1<<30)) >> 30, (plane & np.uint64(0b1<<29)) >> 29, (plane & np.uint64(0b1<<28)) >> 28
        , (plane & np.uint64(0b1<<27)) >> 27, (plane & np.uint64(0b1<<26)) >> 26, (plane & np.uint64(0b1<<25)) >> 25, (plane & np.uint64(0b1<<24)) >> 24
        , (plane & np.uint64(0b1<<23)) >> 23, (plane & np.uint64(0b1<<22)) >> 22, (plane & np.uint64(0b1<<21)) >> 21, (plane & np.uint64(0b1<<20)) >> 20
        , (plane & np.uint64(0b1<<19)) >> 19, (plane & np.uint64(0b1<<18)) >> 18, (plane & np.uint64(0b1<<17)) >> 17, (plane & np.uint64(0b1<<16)) >> 16
        , (plane & np.uint64(0b1<<15)) >> 15, (plane & np.uint64(0b1<<14)) >> 14, (plane & np.uint64(0b1<<13)) >> 13, (plane & np.uint64(0b1<<12)) >> 12
        , (plane & np.uint64(0b1<<11)) >> 11, (plane & np.uint64(0b1<<10)) >> 10, (plane & np.uint64(0b1<<9)) >> 9, (plane & np.uint64(0b1<<8)) >> 8
        , (plane & np.uint64(0b1<<7)) >> 7, (plane & np.uint64(0b1<<6)) >> 6, (plane & np.uint64(0b1<<5)) >> 5, (plane & np.uint64(0b1<<4)) >> 4
        , (plane & np.uint64(0b1<<3)) >> 3, (plane & np.uint64(0b1<<2)) >> 2, (plane & np.uint64(0b1<<1)) >> 1, (plane & np.uint64(0b1<<0)) >> 0]
    return np.concatenate(list(zip(*a)))

def send(IPaddr, port, depth, nchannels, rate, chunk_size, dwt_levels, sent, max_sent):
    audio = pyaudio.PyAudio()                                      # Create the audio handler.
    stream = audio.open(format=audio.get_format_from_width(depth), # Configure the sound card.
                        channels=nchannels,
                        rate=rate,
                        input=True,
                        frames_per_buffer=chunk_size)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)           # Create an UDP socket.

    while True:                                                       # Forever.
        sent.value += 1                                               # Number of sent chunks.
        data = stream.read(chunk_size, exception_on_overflow=False)    # Read a chunk from the sound card.
        samples = np.frombuffer(data, dtype=np.int16)                 # Converts the chunk to a Numpy array.
        #if __debug__:
        #    counter = 0
        #    for i in samples:
        #        print('i ' + str(i))
        #        counter += 1
        #        if counter > 10:
        #            break
        max_sent.value = np.max(np.abs(samples))
        coeffs = pywt.wavedec(samples, "db1", level=dwt_levels)       # Multilevel forward wavelet transform, coeffs = [cA_n, cD_n, cD_n-1, …, cD2, cD1]: list, where n=dwt_levels.
        bitplanes = create_bitplanes(coeffs)                          # A list of 32 bitplanes.
        for i in range(32):                                           # For all bitplanes.
            sock.sendto(bitplanes[i].tobytes(), (IPaddr, port))       # Send the bitplane.

def receive(port, depth, nchannels, rate, chunk_size, dwt_levels, received, max_received):
    audio = pyaudio.PyAudio()                                      # Create the audio handler.
    stream = audio.open(format=audio.get_format_from_width(depth), # Configure the sound card.
                        channels=nchannels,
                        rate=rate,
                        output=True,
                        frames_per_buffer=chunk_size)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listening_at = ("0.0.0.0", port)
    sock.bind(listening_at)

    # Create buffer
    bitplanes = [None]*32
    while True:
        for i in range(31,-1,-1):
            bitplane, addr = sock.recvfrom(4096)
            bitplanes[i] = np.frombuffer(bitplane, dtype=np.int8)
        received.value += 1
        subbands = create_subbands(bitplanes, dwt_levels)
        samples = pywt.waverec(subbands, "db1").astype(np.int16)
        samples = np.random.rand(1024).astype(np.int16)
        if __debug__:
            counter = 0
            for i in samples:
                print('o ' + str(i))
                counter += 1
                if counter > 10:
                    break            
        max_received.value = np.max(np.abs(samples))
        stream.write(samples.tobytes())

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
