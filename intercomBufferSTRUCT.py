# No video, no DWT, no compression, no bitplanes, no data-flow
# control, no buffering. Only the transmission of the raw audio data,
# splitted into chunks of fixed length.
#
# https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py

# SOULUTION 1 working solution

#IMPLEMENTATION:
#Current VERSION 1.7
#1.7    -changed unpack method. Use without numpy.delete/numpy.insert

#1.6    -Added comments for explanation

#1.5    -struct for correct byte order

#1.4    -CPU and size measurement

#1.3    -inheritance from parent class

#1.2    -buffer dynamic by argument
#       -implementation of delay of playback

#1.1    -index sent with package

#1.0    -implementation buffer 

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
            self.packet_list.append(numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype))
        self.silence=numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)
        self.packet_send=0

        #Benchmark Variables
        self.cpu_load=0
        self.cpu_max=0
        self.cycle=0       #caculation cycle for average value
        
        #first index -1 for delaying play
        self.packet_received=-1
        
        #calc size of message example: s. per chunk = 1024 & channel=2 (1024*2)
        self.msgsize=(self.samples_per_chunk*self.number_of_channels)

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

            #define message array for unpacking
            message=[]
            #unpack index to index and message to array at pointer *message
            idx, *message=struct.unpack('<H{}h'.format(self.msgsize),messagepack) #unpack structure
            self.packet_list[idx % self.buffer_size]=message    #out[0]=index, out=index & message
            #sys.stderr.write("\nIDX: {} - MSG: {}".format(idx,len(message)));sys.stderr.flush()

            #--------------Benchmark-------------------------
            self.cycle+=1
            cpu=psutil.cpu_percent() / psutil.cpu_count()
            if self.cpu_max<cpu:
                self.cpu_max=cpu
            self.cpu_load+=cpu
            
            #sys.stderr.write("\nMSGB_SIZE:{} CPU_LOAD:{} CPU_MAX:{}".format(
            #    sys.getsizeof(messagepack),
            #    (self.cpu_load/self.cycle),
            #    self.cpu_max)); sys.stderr.flush();
            #--------------Benchmark END---------------------

        def record_send(indata, outdata, frames, time, status):
            data=numpy.frombuffer(
                indata,
                numpy.int16)

            datapack=struct.pack('<H{}h'.format(self.msgsize),self.packet_send,*data)
            sending_sock.sendto( 
                datapack,
                (self.destination_IP_addr, self.destination_port))
            self.packet_send=(self.packet_send+1)%(2**16)

            if self.packet_received<0:
                nonzeros=[]           
                for s in range(self.buffer_size):
                    #has to be <= 1 because size of empty message & index is 1
                    if numpy.array_equal(self.packet_list[s],self.silence)==False:
                        nonzeros.append(s)
                if len(nonzeros)>0:
                    print("NONZEROS: {} MAX: {}, MIN {}".format(nonzeros,max(nonzeros),min(nonzeros)))
                    if max(nonzeros)-min(nonzeros) >= (math.ceil(self.buffer_size/2)-1): 
                        self.packet_received=nonzeros[0]
                        print("\nBUFFERING FINISHED - START PLAYING")
                    else:
                        print("\nBUFFER NOT FILLED")
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()
                
        def record_send_and_play(indata, outdata, frames, time, status):
            #get message from stream and write to data array
            data=numpy.frombuffer(
                indata,
                numpy.int16)
            #Put index and data in structure and define "little-endian" format with size of messages and index ("<")
            #H = unsigned short integer (0 - 65535) for index (2^16), h = signed short integer (-32768 - 32767)
            #example: 1024 samples, 2 cahnnels =  '<H2048h'
            datapack=struct.pack('<H{}h'.format(self.msgsize),self.packet_send,*data)
            
            sending_sock.sendto( 
                datapack,
                (self.destination_IP_addr, self.destination_port))

            #calc next index, if bigger than 65535 reset to zero
            self.packet_send=(self.packet_send+1)%(2**16)

            #check non-zero elements in buffer for delaying playback

            message=self.packet_list[self.packet_received]

            #if we started playing (after buffer was filled more than half-size) increase received counter
            self.packet_list[self.packet_received]=numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)
                
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
                callback=record_send):
            print('-=- Press <CTRL> + <C> to quit -=-')
            while self.packet_received<0:
                receive_and_buffer()

        print('\n-=- START PLAYING -=-')
        with sd.Stream(
                samplerate=self.samples_per_second,
                blocksize=self.samples_per_chunk,
                dtype=self.dtype,
                channels=self.number_of_channels,
                callback=record_send_and_play):
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
        parser.set_defaults(samples_per_chunk=512)
        args = parser.parse_args()
        return args
    
if __name__ == "__main__":
    intercom2 = IntercomBuffer()
    args=intercom2.parse_args()
    intercom2.init(args)
    intercom2.run()
