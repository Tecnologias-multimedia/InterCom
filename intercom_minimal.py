#!/usr/bin/env python3
import sounddevice as sd                                                        
import numpy as np  
assert np  # avoid "imported but unused" message (W0611)                                                            
import argparse                                                                 
import socket                                                                   
import sys
        

class Intercom:

    MAX_MESSAGE_SIZE = 32768                                                    # In bytes
    
    def add_args(self):
        parser = argparse.ArgumentParser(description="Real-time intercom", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-s", "--frames_per_chunk", help="Samples per chunk.", type=int, default=1024)
        parser.add_argument("-r", "--frames_per_second", help="Sampling rate in frames/second.", type=int, default=44100)
        parser.add_argument("-c", "--number_of_channels", help="Number of channels.", type=int, default=2)
        parser.add_argument("-p", "--mlp", help="My listening port.", type=int, default=4444)
        parser.add_argument("-i", "--ilp", help="Interlocutor's listening port.", type=int, default=4444)
        parser.add_argument("-a", "--ia", help="Interlocutor's IP address or name.", type=str, default="localhost")
        return parser
        
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
        self.chunk99 = np.zeros((self.frames_per_chunk, self.number_of_channels), np.int16)

        print(f"number_of_channels={self.number_of_channels}")
        print(f"frames_per_second={self.frames_per_second}")
        print(f"frames_per_chunk={self.frames_per_chunk}")
        print(f"samples_per_chunk={self.samples_per_chunk}")
        print(f"listening_port={self.listening_port}")
        print(f"destination_IP_address={self.destination_IP_addr}")
        print(f"destination_port={self.destination_port}")
        print(f"bytes_per_chunk={self.bytes_per_chunk}")


    def receive(self):
        #import time    
            #time.sleep(0.1)
        for i in range(100000):
            pass
        message, source_address = self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_SIZE)
        chunk = np.frombuffer(message, np.int16).reshape(self.frames_per_chunk, self.number_of_channels)
        self.chunk99 = chunk
    
    
    def send(self, data):
        self.sending_sock.sendto(data, (self.destination_IP_addr, self.destination_port))
        
    def record_send_and_play(self, indata, outdata, frames, time, status):
        self.send(indata)
        outdata[:] = self.chunk99
        sys.stderr.write("."); sys.stderr.flush()
            
    def run(self):
        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=self.record_send_and_play):
            print('#' * 80)
            print('press <CTRL> + <c> to quit')
            print('#' * 80)
            while True:
                self.receive()
                
if __name__ == "__main__":
    intercom = Intercom()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
