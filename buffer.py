import ctypes
import select
import sys
import getopt
from socket import socket, AF_INET, SOCK_DGRAM
import numpy as np
import sounddevice as sd
from time import sleep
from minimal import Minimal

class Buffer(Minimal):

    def __init__(self, ip="127.0.0.1", port=4444):

        self.send_id = ctypes.c_uint16(0)
        self.recv_id = ctypes.c_uint16(0)
        self.number_cells = 6
        # Buffering time to cells
        # self.numbers_cells = math.ceil(self.buffering/self.chunk_time)
        self.ready_frames = 0
        self.ready_to_play = False
        self.first_run = True
        self.lost_packets = 0

        self.dst_addr = ip
        self.udp_port = port

        self.samplerate = 44100
        self.blocksize = 4096
        self.channels = 2
        self.max_payload_bytes = (self.blocksize * 2 + 1) * 2

        self.send_buffer = (ctypes.c_int16 * (self.blocksize * 2 + 1))()
        self.recv_buffer = (ctypes.c_int16 * (self.blocksize * 2 + 1))()

        self.cyclic_buffer = \
            ((ctypes.c_int16 * (self.blocksize * 2 + 1)) * self.number_cells)()

        self.sending_socket = socket(AF_INET, SOCK_DGRAM)
        self.receiving_socket = socket(AF_INET, SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", self.udp_port)
        self.receiving_socket.bind(self.listening_endpoint)
        self.chunk_time = self.blocksize / self.samplerate
        self.receiving_socket.settimeout(self.chunk_time)

    # We overwrite the send method
    def send(self, packed_chunk):
        self.sending_socket.sendto(packed_chunk,
                                   (self.dst_addr, self.udp_port))

    # We overwrite the stream method
    def stream(self):
        return sd.Stream(dtype=self.SAMPLE_TYPE,
                         samplerate=self.samplerate,
                         blocksize=self.blocksize,
                         channels=self.channels,
                         callback=self._rsp)

    # We use this function to increment
    # self.ready_frames 'cause Python
    # doesn't support '++'... Sigh...
    def _inc_frames(self):
        self.ready_frames += 1
        return self.ready_frames

    # Record, Send & Play
    def _rsp(self, indata, outdata, *_):
        # Pack
        self.send_buffer[0] = self.send_id.value
        self.send_buffer[1:] = indata.flatten()
        self.send_id.value += 1

        # Send
        self.send(self.send_buffer)

        # Play
        if self.ready_to_play:
            pos = self.recv_id.value % self.number_cells
            uid = ctypes.c_uint16(self.cyclic_buffer[pos][0])  # "casteamos"

            if self.recv_id.value != uid.value:
                self.lost_packets += 1
                outdata.fill(0)
            else:
                # Can be done with
                # np.reshape(self.RECV_BUFFER[1:], (-1, 2))
                # but just to make sure we copy the array
                # specifying dtype='int16'
                data = np.array(self.cyclic_buffer[pos][1:], dtype='int16')
                data = np.reshape(data, (-1, 2))
                outdata[:] = data

            self.recv_id.value += 1
        else:
            outdata.fill(0)

    # Receive & Buffer
    def _rb(self):
        readable, [], [] = select.select([self.receiving_socket], [], [], 0)

        # Not sure if I should use
        # len(readable) or readable...
        if len(readable) > 0:

            # Should we start playing ? Only
            # if we've received 3 chunks
            self.ready_to_play = self.ready_to_play | \
                (self._inc_frames() >= self.number_cells // 2)

            # We get the memory address of the RECV_BUFFER
            mview = memoryview(self.recv_buffer)[0:]
            # then dump the contents of the socket into the temporary buffer
            self.receiving_socket.recv_into(mview, self.max_payload_bytes)
            # We retrieve the packet id from the buffer
            uid = ctypes.c_uint16(self.recv_buffer[0])  # "casteamos"
            # and find out where we should store it
            pos = uid.value % self.number_cells
            # Finally we copy the contents of the temporary buffer
            # into the cyclic buffer
            self.cyclic_buffer[pos][:] = self.recv_buffer

            # To prevent packet loss when desynchronized
            # (only applies to first run)
            if self.first_run:
                self.recv_id = uid
                self.first_run = False

    def run(self):
        with self.stream():
            while True:
                self._rb()
                ready = '\033[0;32m✔\033[0m' if self.ready_to_play\
                    else '\033[0;31m✗\033[0m'
                print(f"Sending {ready}\
                       \tSend id: {self.send_id.value}\
                       \tReceive id: {self.recv_id.value}\
                       \tLost packets: {self.lost_packets}",
                      end="\r", flush=True)


if __name__ == "__main__":

    ip = "127.0.0.1"
    port = 4444

    argv = sys.argv[1:]

    try:
        opts, args = getopt.getopt(argv, "i:p:",
                                   ["ip_address =",
                                    "port ="])
    except:
        print("buffer.py -i <ip_address> -p <port>")
        exit(1)

    for opt, arg in opts:
        if opt in ['-i', '--ip_address']:
            ip = arg
        elif opt in ['-p', '--port']:
            port = int(arg)

    print(f"Connecting to {ip}:{port} 🧐")

    intercom = Buffer(ip, port)

    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nBye! 😃")
