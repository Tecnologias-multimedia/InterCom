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

minimal.parser.add_argument("-qs", "--minimal_quantized_step", type=int, default=1, help="Quantized step")

class BR_Control(compress.Compression):
    def __init__(self):
        if __debug__:
            print("Running BR_Control.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (BR_Control) is running")
        self.quantized_step = minimal.args.minimal_quantized_step
        print("quantized step =", minimal.args.minimal_quantized_step)
        self.sent_chunks = 0
        self.received_chunks = 0
        self.lost_packets = 0  

    def quantize(self, chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        quant = np.round(chunk / self.quantized_step).astype(dtype)
        return quant

    def dequantize(self, chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        dequant = (self.quantized_step * chunk).astype(dtype)
        return dequant  

    def pack(self, chunk_number, chunk):
        quantized_chunk = self.quantize(chunk)
        quantized_chunk = super().pack(chunk_number, quantized_chunk)
        self.sent_chunks += 1
        return quantized_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        chunk = self.dequantize(chunk)
        self.received_chunks += 1
        return chunk_number, chunk

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

    intercom = BR_Control()

    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
