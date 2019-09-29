# No video, no DWT, no compression, no bitplanes, no data-flow
# control, no buffering. Only the transmission of the raw audio data,
# splitted into chunks of fixed length.
#
# https://github.com/Tecnologias-multimedia/intercom
#
# Based on: https://python-sounddevice.readthedocs.io/en/0.3.13/_downloads/wire.py


import sounddevice as sd 
import intercom as intercomOriginal
import numpy                                                                    # https://numpy.org/
import argparse                                                                 # https://docs.python.org/3/library/argparse.html
import socket  

if __debug__:
    import sys
    
packet_send=0
packet_received=0
packet_list=[[],[],[],[]]
buffer_size=4
    
class IntercomBuffer(intercomOriginal.Intercom):

    def run(self):
        sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listening_endpoint = ("0.0.0.0", self.listening_port)
        receiving_sock.bind(listening_endpoint)
        
        def receive_and_buffer():
            global packet_list
            global buffer_size
            messagepack, source_address = receiving_sock.recvfrom(
                intercomOriginal.Intercom.max_packet_size)
            
            out=numpy.frombuffer(messagepack,numpy.int16)
            idx=out[0]
            message=numpy.delete(out,0)
            packet_list[idx%buffer_size]=message
            #sys.stderr.write("\nIDX_REC:" + str(idx)); sys.stderr.flush()
            
        def record_send_and_play(indata, outdata, frames, time, status):
            global packet_received
            global packet_list
            global buffer_size
            global packet_send
            
            datapack=numpy.insert(numpy.frombuffer(
                indata,
                numpy.int16),0,packet_send)
            
            sending_sock.sendto( 
                datapack,
                (self.destination_IP_addr, self.destination_port))
            packet_send=packet_send+1
            #sys.stderr.write("\nIDX_SEND:" + str(packet_send-1)); sys.stderr.flush()
            
            try:
                message=packet_list[packet_received % buffer_size]
                #sys.stderr.write("\nmessage:" + str(message)); sys.stderr.flush()
                
                if len(message)==0:
                    raise ValueError
            except ValueError:
                message = numpy.zeros(
                    (self.samples_per_chunk, self.bytes_per_sample),
                    self.dtype)
            
            packet_received=packet_received+1
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

if __name__ == "__main__":

    intercom = IntercomBuffer()
    args = intercom.parse_args()
    intercom.init(args)
    intercom.run()
