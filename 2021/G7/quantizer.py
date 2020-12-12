import zlib
import numpy as np
import struct
import math
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import buffer
import compress
import time

# Used to chek if tc rule exists
import pyroute2
from pyroute2 import IPRoute


class Interface_Data:
    """Checks network interface status. Tries to find whether
    tc rules that limits bitrate exists
    """

    def __init__(self):
        self.ip = pyroute2.IPRoute()
        self.ipr = IPRoute()
        self.rate = None
    def get_rate(self, qdisc_list):
        for i in qdisc_list :
            if "TCA_OPTIONS" in i:
                params = i[1].get('attrs')
                for j in params:
                    if 'TCA_TBF_PARMS' in j:
                        self.rate = j[1].get('rate')
                        break
        if(self.rate is not None):
            self.rate = self.rate / 125
        else:
            self.rate = None
        return self.rate

    def get_interface_index(self, name):
        return self.ip.link_lookup(ifname=name)

    def get_qdisc_atributes(self, interface):
        return self.ipr.get_qdiscs(interface)[0].get('attrs')

    def search(self):
        self.rate = None
        interface = self.get_interface_index("lo")
        if(len(interface) == 1):
            atributes = self.get_qdisc_atributes(interface[0])
            if(atributes is not None):
                self.get_rate(atributes)
        return self.rate


minimal.parser.add_argument("-q", "--quantization_step", type=int, default=1, help="Quantization step")
minimal.parser.add_argument("-per", "--periods", type=int, default=10, help="Periodos")

class BR_Control(compress.Compression): #(compress.Compression__verbose):
    """Tries to control the bitrate via quantization. Quantization jeopardises
    the quality but helps to reduce te bitrate needed to received packages
    """

    def __init__(self):
        super().__init__()
        self.periods = minimal.args.periods
        self.quantization_step = minimal.args.quantization_step
        self.quantization_bits = 16
        self.dynamic_range = 65535
        self.rate = 1
        self.start_time = time.time()
        self.interface_data = Interface_Data()
        self.last_time = time.time()
        self.bitrate = 44100 * 2 * 16
        self.moving_average_sent = np.full(self.periods, 1441/2)
        self.average_sent = 1441
        self.kbp_sent_counter = 0
        self.counter_packages_sent = 0
        self.received_packages_sent = 0
        self.min_quantization_step = 1
        self.max_quantization_step = 300
        self.maximo = 0
        self.expected_package_size = 2048 * 16 * 2
        self.acumulative_std = 0
        self.average_std = 0

        self.sender_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk * minimal.Minimal.NUMBER_OF_CHANNELS], dtype=np.int16)

        self.receiver_chunk_buffer = np.zeros([buffer.minimal.args.frames_per_chunk, minimal.Minimal.NUMBER_OF_CHANNELS], dtype = np.int16)

        self.sender_buf_size = len(self.sender_chunk_buffer)

        self.receiver_buf_size = len(self.receiver_chunk_buffer)


    def deadzone_quantizer(self, x, quantization_step):
        """Quantizrr function. Apply quantization to input data
        using the quantization step provided
        """

        if(quantization_step == 0):
            quantization_step = 1
        k = (x / quantization_step).astype(np.int16)
        return k

    def deadzone_dequantizer(self, k, quantization_step):
        """Dequantizer function. Apply dequantization to data
        using the quantization step provided
        """

        y = quantization_step * k
        return y

    def pack(self, chunk_number, chunk):
        '''Builds a packed packet with a compressed chunk and a chunk_number.
        Applies quantization to reduce the size needed.

        '''

        self.acumulative_std += np.std(chunk)
        channel_0 = chunk[:, 0].copy()
        channel_1 = chunk[:, 1].copy()
        plane_chunk = np.concatenate([channel_0, channel_1])

        # Applies quantization
        plane_chunk = self.deadzone_quantizer(plane_chunk, self.quantization_step)

        # Compress the package
        compressed_chunk = zlib.compress(plane_chunk,1)

        packed_chunk = struct.pack("!Hf", chunk_number, self.quantization_step) + compressed_chunk

        # Get statistical data for next quantization step calculaton
        self.kbp_sent_counter += len(packed_chunk)
        if(self.maximo < len(packed_chunk)):
            self.maximo=len(packed_chunk)*0.9
        self.counter_packages_sent += 1

        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        '''Gets the chunk number and the chunk audio from packed_chunk.
        Dequantize the package using the suitable quantization step

        '''

        # Quantization step is adjusted in unpack
        self.adjust_and_bitrate()

        (chunk_number, step) = struct.unpack("!Hf", packed_chunk[:6])

        compressed_chunk = packed_chunk[6:]
        decompressed_chunk = zlib.decompress(compressed_chunk)
        decompressed_chunk = np.frombuffer(decompressed_chunk, dtype)

        # Dequantize the package
        decompressed_chunk = self.deadzone_dequantizer(decompressed_chunk, step)
        chunk = np.column_stack((decompressed_chunk[0:int(len(decompressed_chunk)/2)], decompressed_chunk[int(len(decompressed_chunk)/2): int(len(decompressed_chunk))]))

        return chunk_number, chunk

    def adjust_and_bitrate(self):
        """Get the current bitrate limitation checking the network
        interface and adjust the statistical data retrieved.
        """

        interval = time.time() - self.last_time
        if(interval>= 1):
            self.bitrate = self.interface_data.search()
            if(not self.bitrate):
                self.bitrate = 5000
            self.moving_average_sent = np.roll(self.moving_average_sent, -1)

            self.moving_average_sent[-1] = (self.maximo * 8 * self.counter_packages_sent / 1000) / interval
            self.average_std = self.acumulative_std / self.counter_packages_sent
            self.acumulative_std = 0
            self.kbp_sent_counter = 0

            self.counter_packages_sent = 0
            self.average_sent = np.average(self.moving_average_sent)

            self.adjust_delta()
            self.last_time = time.time()
            self.maximo = 0

    def adjust_delta(self):
        """Function that adjust delta using the current estimated
        bitrate.
        """

        if((self.bitrate < self.average_sent) or (self.bitrate < self.moving_average_sent[-1])):
            rate = self.average_sent - self.bitrate if (self.average_sent < self.moving_average_sent[-1]) else self.moving_average_sent[-1] - self.bitrate
            self.quantization_step = self.quantization_step + math.sqrt(abs(rate))
            if(self.quantization_step > self.max_quantization_step):
                self.quantization_step = self.max_quantization_step

        elif(self.bitrate > self.average_sent):
            if(self.average_std > 150):
                rate = self.bitrate - self.average_sent
                self.quantization_step = self.quantization_step - math.sqrt(rate)
                if(self.quantization_step < self.min_quantization_step):
                    self.quantization_step = self.min_quantization_step


class BR_Control_Verbose(BR_Control, compress.Compression__verbose):
    def __init__(self):
        super().__init__()

    def averages(self):
        string = super().averages()
        string += "{:8d}".format(int(self.quantization_step))
        string += "{:8d}".format(int(self.average_sent))
        string += "{:8d}".format(int(self.average_std))
        return string

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = BR_Control_Verbose()
    else:
        intercom = BR_Control()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")