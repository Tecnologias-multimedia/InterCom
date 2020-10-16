# Minimal Intercom

import argparse
import logging
import socket


try:
    import sounddevice as sd
except ModuleNotFoundError:
    import os
    os.system("pip3 install sounddevice --user")
    import sounddevice as sd

try:
    import numpy as np
except ModuleNotFoundError:
    print("Installing numpy with pip")
    import os
    os.system("pip3 install numpy --user")
    import numpy as np

try:
    import psutil
except ModuleNotFoundError:
    import os
    os.system("pip3 install psutil --user")
    import psutil




class MinimalIntercom:

    CHANNELS = 2

    SAMPLE_RATE = 44100

    CHUNK_SIZE = 1024

    SOURCE_PORT = 7676

    DESTINATION_PORT = 7676

    DESTINATION_IP = "localhost" #"192.168.1.37"

    MAX_PAYLOAD_BYTES =  32768

    NUMPY = 1

    # Expected TCP connection for synchronize variables, however
    # at this moment, variables would be passed in constructor

    def __init__(self, args):
        # self.channels = argument["key"]  if "channels" in arguments else self.channels = CHANNELS
        self.channels = args.number_of_channels
        self.sample_rate = args.frames_per_second
        self.chunk_size = args.frames_per_chunk
        self.source_port = args.source_port
        self.destination_IP = args.destination_IP
        self.destination_port = args.destination_port



        # Endpoints pair decalration
        self.sender_endpoint = (self.destination_IP, self.destination_port)
        self.receiver_endpoint = ("0.0.0.0", self.source_port)

        # Socket definition
        self.sender_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.receiver_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Bind listener socket
        self.receiver_socket.bind(self.receiver_endpoint)

        # Stream parameters

        if MinimalIntercom.NUMPY == 1:
            self.data_type = np.int16
        else:
            self.data_type = "int16"
        self.zero_chunk = self.generate_zero_chunk()
        # Print parameters
        self.data=self.generate_zero_chunk()

    def __del__(self):
        self.receiver_socket.close()

    def generate_zero_chunk(self):
        return np.zeros((self.chunk_size, self.channels), self.data_type)

    def send(self, data):
        self.sender_socket.sendto(data,  (self.destination_IP, self.destination_port)) #self.sender_endpoint)

    def receive(self):
        data, status = self.receiver_socket.recvfrom(self.MAX_PAYLOAD_BYTES)

        if not data:
            data = self.zero_chunk
        else:
            data = np.frombuffer(data, np.int16).reshape(self.chunk_size, self.channels)
        #if data:
        #    print("NO DATA")
        #    data = self.generate_zero_chunk()
        self.data = data

    def callback(self, indata, outdata, frames, time, status):
        #if status:
        #    print(status)

        #self.receive()

        self.send(indata)

        outdata[:] = self.data


    def start(self):
        if MinimalIntercom.NUMPY == 1:
            with sd.Stream(samplerate = self.sample_rate, blocksize = self.chunk_size,
                           dtype = self.data_type, channels = self.channels,
                           callback = self.callback):

                while True:
                    self.receive()
                #   print('#' * 80)
                #   print('press Return to quit')
                #   print('#' * 80)
                #   input()

        else:
            with sd.RawStream(samplerate = self.sample_rate, blocksize = self.chunk_size,
                           dtype = self.data_type, channels = self.channels,
                           callback = self.callback):
                pass

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
                            type=int, default=MinimalIntercom.CHANNELS)
        parser.add_argument("-p", "--source_port",
                            help="My listening port.",
                            type=int, default=MinimalIntercom.SOURCE_PORT)
        parser.add_argument("-i", "--destination_port",
                            help="Interlocutor's listening port.",
                            type=int, default=MinimalIntercom.DESTINATION_PORT)
        parser.add_argument("-a", "--destination_IP",
                            help="Interlocutor's IP address or name.",
                            type=str, default=MinimalIntercom.DESTINATION_IP)
        return parser

#Global variable declaration


"""
class MinimalIntercom2:

    def __init__(self, dest_IP, dest_Port):
    #Definimos un socket de familia direccion puerto (AF_INET)
    # y de tipo UDP (SCK_DGRAM)
        self.UDPsocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.stream = sd.RawStream(samplerate=44100, channels=2, dtype='int16')
        self.stream.start()

    # Ligamos el socket
        self.UDPsocket.bind((dest_IP, dest_Port))



    def send(self):
        chunk, overflowed = self.stream.read(1024)
        self.UDPsocket.sendto(chunk, ("127.0.0.1", 7777))

    def receive(self):
        chunk,server=self.UDPsocket.recvfrom(7777);
        self.stream.write(chunk)


intercom = MinimalIntercom("127.0.0.1",7777);
while True:
    intercom.send()
    intercom.receive()

#intercom.send(b"Wepale");
#intercom.receive()
"""


# Empieza el programa
if __name__ == "__main__":
 # intercom = MinimalIntercom()
    parser_arguments = MinimalIntercom.add_args()
    args = parser_arguments.parse_args()
    print(args)
    intercom = MinimalIntercom(args)
    intercom.start()

    try:
        intercom.start()
    except KeyboardInterrupt:
        parser_arguments.exit(1,"\n Interrupted by user")
    except Exception as e:
        parser_arguments.exit(1, type(e).__name__ + ': ' + str(e))


