#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (lossless compression of the chunks). '''

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
import threading
import time

minimal.parser.add_argument("-q", "--minimal_quantized_step", type=int, default=1, help="Quantized step")

class BR_Control(compress.Compression):
    def __init__(self):
        if __debug__:
            print("Running BR_Control.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (BR_Control) is running")
        self.quantized_step = minimal.args.minimal_quantized_step
        print("(minimum) quantized step =", minimal.args.minimal_quantized_step)
        self.sent_chunks = 0
        self.received_chunks = 0
        self.lost_packets = 0
        data_flow_control_thread = threading.Thread(target=self.bucle)
        data_flow_control_thread.daemon = True
        data_flow_control_thread.start()  

    def bucle(self):
        while True:
            self.lost_packets = self.sent_chunks - self.received_chunks
            self.quantized_step += self.lost_packets
            if self.quantized_step < minimal.args.minimal_quantized_step:
                self.quantized_step =  minimal.args.minimal_quantized_step
            self.sent_chunks = 0
            self.received_chunks = 0
            time.sleep(2)	

    def deadzone_quantizer(self, x, dtype=minimal.Minimal.SAMPLE_TYPE):
        k = np.round(x / self.quantized_step).astype(dtype)
        return k

    def deadzone_dequantizer(self, k, dtype=minimal.Minimal.SAMPLE_TYPE):
        y = (self.quantized_step * k).astype(dtype)
        return y  

    def pack(self, chunk_number, chunk):
        quantized_chunk = self.deadzone_quantizer(chunk)
        quantized_chunk = super().pack(chunk_number, quantized_chunk)
        self.sent_chunks += 1
        return quantized_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        chunk = self.deadzone_dequantizer(chunk)
        self.received_chunks += 1
        return chunk_number, chunk

class BR_Control__verbose(BR_Control, compress.Compression__verbose):
    def __init__(self):
        if __debug__:
            print("Running BR_Control__verbose.__init__")
        super().__init__()
        self.variance = np.zeros(self.NUMBER_OF_CHANNELS) # Variance of the chunks_per_cycle chunks.
        self.entropy = np.zeros(self.NUMBER_OF_CHANNELS) # Entropy of the chunks_per_cycle chunks.
        self.bps = np.zeros(self.NUMBER_OF_CHANNELS) # Bits Per Symbol of the chunks_per_cycle compressed chunks.
        self.chunks_in_the_cycle = []

        self.average_variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_entropy = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_bps = np.zeros(self.NUMBER_OF_CHANNELS)
        
    def stats(self):
        string = super().stats()
        string += " {}".format(['{:4.1f}'.format(self.quantized_step)])
        return string

    def first_line(self):
        string = super().first_line()
        string += "{:8s}".format('') # quantized_step
        return string

    def second_line(self):
        string = super().second_line()
        string += "{:>8s}".format("QS") # quantized_step
        return string

    def separator(self):
        string = super().separator()
        string += f"{'='*(20)}"
        return string

    def averages(self):
        string = super().averages()
        return string
        
    def entropy_in_bits_per_symbol(self, sequence_of_symbols):
        value, counts = np.unique(sequence_of_symbols, return_counts = True)
        probs = counts / len(sequence_of_symbols)
        #n_classes = np.count_nonzero(probs)

        #if n_classes <= 1:
        #    return 0

        entropy = 0.
        for i in probs:
            entropy -= i * math.log(i, 2)

        return entropy

    def cycle_feedback(self):
        super().cycle_feedback()

'''
    def _record_send_and_play(self, indata, outdata, frames, time, status):
        super()._record_send_and_play(indata, outdata, frames, time, status)
        self.chunks_in_the_cycle.append(indata)
        # Remember: indata contains the recorded chunk and outdata,
        # the played chunk.

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])
        len_compressed_channel_1 = len(packed_chunk[len_compressed_channel_0+4:])

        self.bps[0] += len_compressed_channel_0*8
        self.bps[1] += len_compressed_channel_1*8
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        return chunk_number, chunk
'''

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
        intercom = BR_Control__verbose()
    else:
        intercom = BR_Control__verbose()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
