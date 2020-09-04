#
# Intercom_minimal
# |
# +- Intercom_buffer
#    |
#    +- Intercom_bitplanes
#
# Transmits the chunks of audio by bitplanes, staring at the most
# significant (15) one and ending with the least significant (0), each
# bitplane in a different packet.
#

# To-do:
#
# Explain why if we change the line:
#
#   self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
#
# by the line:
# 
#   self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.empty_chunk
#
# in the method Intercom_buffer::play_chunk(), intercom_bitplanes.py does not work. 


from intercom_minimal import Intercom_minimal
from intercom_buffer import Intercom_buffer
import sounddevice as sd
import numpy as np
import struct
import sys
import time
from multiprocessing import Value
import psutil

# Accumulated percentage of used CPU. 
CPU_total = 0

# Number of samples of the CPU usage.
CPU_samples = 0

# CPU usage average.
CPU_average = 0

class Intercom_bitplanes(Intercom_buffer):

    def init(self, args):
        # The feedback to the user is shown by the feedback() method,
        # in a different process. To share data between the both
        # processes we will use the Value class of multiprocessing.
        self.sent_messages_counter = Value('i', 0)
        self.received_messages_counter = Value('i', 0)
        self.sent_bytes_counter = Value('i', 0)
        self.received_bytes_counter = Value('i', 0)

        Intercom_buffer.init(self, args)
        self.packet_format = f"!HB{self.frames_per_chunk//8}B" # Quitar
        self.number_of_bitplanes = 16
        self.number_of_bitplanes_to_send = self.number_of_bitplanes * self.number_of_channels

        print("Intercom_bitplanes: transmitting by bitplanes ...")

    # Now, each packet transports a bitplane of a chunk (in the
    # previous intercom's each packet transported a complete
    # chunk). Again, this is a blocking method that waits for a
    # bitplane and inserts it in a chunk stored in the buffer.
    def receive_and_buffer(self):
        message = self.receive() #self.receiving_sock.recvfrom(Intercom.MAX_MESSAGE_BYTES)
        received_chunk_number, received_bitplane_number, *bitplane = struct.unpack(self.packet_format, message)
        bitplane = np.asarray(bitplane, dtype=np.uint8)
        bitplane = np.unpackbits(bitplane)
        bitplane = bitplane.astype(self.sample_type)
        self._buffer[received_chunk_number % self.cells_in_buffer][:, received_bitplane_number % self.number_of_channels] |= (bitplane << received_bitplane_number//self.number_of_channels)
        return received_chunk_number

    # Sends a bitplane of the last recorded chunk.
    def send_bitplane(self, chunk, bitplane_number):
        bitplane = (chunk[:, bitplane_number%self.number_of_channels] >> bitplane_number//self.number_of_channels) & 1
        bitplane = bitplane.astype(np.uint8)
        bitplane = np.packbits(bitplane)
        message = struct.pack(self.packet_format, self.recorded_chunk_number, bitplane_number, *bitplane)
        self.send_message(message)
        #self.sending_sock.sendto(message, (self.destination_address, self.destination_port))

    # Sends the last recorded chunk (indata).
    def send_chunk(self, indata):
        last_bitplane_to_send = self.number_of_bitplanes*self.number_of_channels - self.number_of_bitplanes_to_send
        for bitplane_number in range(self.number_of_bitplanes*2-1, last_bitplane_to_send, -1):
            self.send_bitplane(indata, bitplane_number)
        #self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.CHUNK_NUMBERS

    def send_message(self, message):
        Intercom_minimal.send(self, message)
        self.sent_messages_counter.value += 1
        self.sent_bytes_counter.value += len(message)

    def receive(self):
        message = Intercom_minimal.receive(self)
        self.received_messages_counter.value += 1
        self.received_bytes_counter.value += len(message)
        return message

    def print_feedback_message(self):
        # Be careful, variables updated only in the subprocess.
        global CPU_total
        global CPU_samples
        global CPU_average
        CPU_usage = psutil.cpu_percent()
        CPU_total += CPU_usage
        CPU_samples += 1
        CPU_average = CPU_total/CPU_samples
        #print(f"{int(CPU_usage)}/{int(CPU_average)}", flush=True, end=' ')
        elapsed_time = time.time() - self.old_time
        self.old_time = time.time()
        sent = int(self.sent_bytes_counter.value*8/1000/elapsed_time)
        received = int(self.received_bytes_counter.value*8/1000/elapsed_time)
        self.total_sent += sent
        self.total_received += received
        print(f"{sent:10d}{received:10d}{self.total_sent:10d}{self.total_received:10d}{self.sent_messages_counter.value:10d}{self.received_messages_counter.value:10d}{int(CPU_usage):5d}{int(CPU_average):5d}")
        self.sent_bytes_counter.value = 0
        self.received_bytes_counter.value = 0
        self.sent_messages_counter.value = 0
        self.received_messages_counter.value = 0
        
    def feedback(self):
        self.old_time = time.time()
        self.total_sent = 0
        self.total_received = 0
        print();
        print(f"{'':>10s}{'':>10s}{'total':>10s}{'total':>10s}{'':>10s}{'':>10s}{'':>5s}{'':>5s}");
        print(f"{'sent':>10s}{'received':>10s}{'sent':>10s}{'received':>10s}{'sent':>10s}{'received':>10s}{'':>3s}{'Average':>5s}");
        print(f"{'kbps':>10s}{'kbps':>10s}{'kbps':>10s}{'kbps':>10s}{'messages':>10s}{'messages':>10s}{'CPU':>5s}{'CPU':>5s}")
        print(f"{'='*70}")
        try:
            while True:
                self.print_feedback_message()
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nIntercom_buffer: average CPU usage = {CPU_average} %")

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("Intercom_buffer: goodbye ¯\_(ツ)_/¯")
