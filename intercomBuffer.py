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
        self.cpu_load=0
        self.cpu_max=0
        self.cycle=0
        self.packet_received=-1 #first index -1 for delaying play

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
            
            out=numpy.frombuffer(messagepack,numpy.int16)   #get 1d-array of message
            idx=out[0]                                      #get value of first position (index o package)
            self.packet_list[idx % self.buffer_size]=out    #save message with index in buffer at position index modulo buffer_size
            self.cycle+=1
            sys.stderr.write("\nMSGSIZE" + str(sys.getsizeof(messagepack))); sys.stderr.flush()
            cpu=psutil.cpu_percent() / psutil.cpu_count()
            if self.cpu_max<cpu:
                self.cpu_max=cpu
            self.cpu_load+=cpu
            sys.stderr.write("\nCPU_LOAD" + str(self.cpu_load/self.cycle)); sys.stderr.flush()
            sys.stderr.write("\nCPU_MAX" + str(self.cpu_max)); sys.stderr.flush()
            
            #sys.stderr.write("\nIDX_REC:" + str(idx)); sys.stderr.flush()
            
        def record_send_and_play(indata, outdata, frames, time, status):
            
            datapack=numpy.insert(numpy.frombuffer(
                indata,
                numpy.int16),0,self.packet_send)            #create datapackage with message and add in first position index of package
            
            sending_sock.sendto( 
                datapack,
                (self.destination_IP_addr, self.destination_port))
            self.packet_send=(self.packet_send+1)%(2**16)
            #sys.stderr.write("\nIDX_SEND:" + str(self.packet_send-1)); sys.stderr.flush()
            
            if self.packet_received<0:
                nonzeros=[]                                     #check non-zero elements in buffer
                for s in range(self.buffer_size):
                    if len(self.packet_list[s])!=0:
                        nonzeros.append(s)

            if self.packet_received<0 and len(nonzeros)>0:  #if buffer is half filled and we havent started playing (packet_received < 0)
                if max(nonzeros)-min(nonzeros) >= math.ceil(self.buffer_size/2): #if distnace between lowest received package and highest on is higher than half-size of buffer, bypass and start playing
                    self.packet_received=nonzeros[0] #get buffer-index of lowest received package
                    print("\nBUFFERING FINISHED - START PLAYING")

            try:
                message=self.packet_list[self.packet_received]
                
                if len(message)<=1:
                    raise ValueError

                idx=message[0]
                message=numpy.delete(message,0)
                sys.stderr.write("\nmessage:" + str(message)); sys.stderr.flush()
    
            except ValueError:
                message = numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)

            if self.packet_received>=0:             #if we started playing (after buffer was filled more than half-size)
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
        parser.add_argument("-bs",
                            "--buffer_size",
                            help="tamaño de buffer",
                            type=int,
                            default=4) 
        parser.set_defaults(samples_per_chunk=1024)
        args = parser.parse_args()
        return args
    
if __name__ == "__main__":
    intercom2 = IntercomBuffer()
    args=intercom2.parse_args()
    intercom2.init(args)
    intercom2.run()
