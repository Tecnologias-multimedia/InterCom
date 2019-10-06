# No video, no DWT, no compression, no bitplanes, no data-flow
# control, no buffering. Only the transmission of the raw audio data,
# splitted into chunks of fixed length.
#
# https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py

# SOULUTION 1 working solution

import sounddevice as sd 
from intercom import Intercom
import numpy                                                                    # https://numpy.org/
import argparse                                                                 # https://docs.python.org/3/library/argparse.html
import socket  
import math
import psutil
import struct

if __debug__:
    import sys
    
class IntercomBuffer(Intercom):

    def init(self, args):
        Intercom.init(self,args)
        self.buffer_size=args.buffer_size
        self.packet_list=[]
        for x in range(self.buffer_size):
            self.packet_list.append([])
        self.packet_send=0

        #Benchmark Variables
        self.cpu_load=0
        self.cpu_max=0
        self.cycle=0       #caculation cycle for average value
        
        #first index -1 for delaying play
        self.packet_received=-1
        
        #calc size of message example: s. per chunk = 1024 & channel=2 & Index = (1024*2)+1
        self.msgsize=(self.samples_per_chunk*self.number_of_channels)+1

        if __debug__:
                print("buffer_size={}".format(self.buffer_size))
            
    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)
        
        def receive_and_buffer():
            messagepack, source_address = receiving_sock.recvfrom(
                Intercom.max_packet_size)
            
            out=struct.unpack('<{}i'.format(self.msgsize),messagepack) #unpack structure
            self.packet_list[out[0] % self.buffer_size]=out    #out[0]=index, out=index & message

            #--------------Benchmark-------------------------
            self.cycle+=1
            #sys.stderr.write("\nMSGSIZE: {}".format(sys.getsizeof(messagepack)));sys.stderr.flush()
            cpu=psutil.cpu_percent() / psutil.cpu_count()
            if self.cpu_max<cpu:
                self.cpu_max=cpu
            self.cpu_load+=cpu
            
            sys.stderr.write("\nMSGB_SIZE:{} CPU_LOAD:{} CPU_MAX:{}".format(
                sys.getsizeof(messagepack),
                (self.cpu_load/self.cycle),
                self.cpu_max)); sys.stderr.flush();
            #--------------Benchmark END---------------------
            
        def record_send_and_play(indata, outdata, frames, time, status):
            #create datapackage with message and add in first position index of package
            data=numpy.insert(numpy.frombuffer(
                indata,
                numpy.int16),0,self.packet_send)
            
            #Put datapack in structure and define "little-endian" format with size of message ("<")
            datapack=struct.pack('<{}i'.format(self.msgsize),*data)
            sys.stderr.write("\nPACKSIZE: {}".format(sys.getsizeof(datapack)));sys.stderr.flush()
            
            sending_sock.sendto( 
                datapack,
                (self.destination_IP_addr, self.destination_port))
            self.packet_send=(self.packet_send+1)%(2**16)

            #check non-zero elements in buffer for delaying playback
            if self.packet_received<0:
                nonzeros=[]                                     
                for s in range(self.buffer_size):
                    #has to be <= 1 because size of empty message & index is 1
                    if len(self.packet_list[s])<=1:
                        nonzeros.append(s)

            #if buffer is half filled and we havent started playing (packet_received < 0)
            if self.packet_received<0 and len(nonzeros)>0:

                #if distnace between lowest received package and highest on is higher than half-size of buffer, bypass and start playing
                if max(nonzeros)-min(nonzeros) >= math.ceil(self.buffer_size/2): 

                    #get buffer-index of lowest received package
                    self.packet_received=nonzeros[0] 
                    print("\nBUFFERING FINISHED - START PLAYING")

            try:
                message=self.packet_list[self.packet_received]

                #if message is empty (no package in buffer[index]) raise error (override message with silence)
                if len(message)<=0:
                    raise ValueError

                idx=message[0]
                message=numpy.delete(message,0)
    
            except ValueError:
                #override message with silence
                message = numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)

            #if we started playing (after buffer was filled more than half-size) increase received counter
            if self.packet_received>=0:             
                self.packet_received=(self.packet_received+1)%self.buffer_size
                
            outdata[:] = numpy.reshape(message,(
                    self.samples_per_chunk, self.number_of_channels))

            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=self.dtype,
                channels=self.number_of_channels,
                callback=record_send_and_play):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while True:
                receive_and_buffer()

    
    def parse_args(self):
        parser = Intercom.add_args(self)

        #add buffer size argument for command line
        parser.add_argument("-bs",
                            "--buffer_size",
                            help="tamaño de buffer",
                            type=int,
                            default=4)

        #overwrite default chunk-size by 1024 if no argument is given (system specific)
        parser.set_defaults(samples_per_chunk=1024)
        args = parser.parse_args()
        return args
    
if __name__ == "__main__":
    intercom2 = IntercomBuffer()
    args=intercom2.parse_args()
    intercom2.init(args)
    intercom2.run()
