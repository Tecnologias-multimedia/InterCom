import argparse
import sounddevice as sd
import numpy as np
import socket
import time
import psutil
import math
import struct
from multiprocessing import Process
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import buffer
import zlib
import minimal
import compress

class BR_Control (compress.Compression):
    
    def __init__(self):
        super().__init__()
        self.quantization_step = 1

    def pack (self, chunk_number, chunk):
        quantized_chunk = self.quantize(chunk)
        packed_chunk = buffer.Buffering.pack(self,chunk_number,chunk)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number,quantized_chunk = buffer.Buffering.unpack(self,packed_chunk, dtype)
        chunk = self.dequantize(quantized_chunk)
        return chunk_number, chunk

    def quantize(self, chunk):
        quantized_chunk = (chunk / self.quantization_step).astype(np.int)
        return quantized_chunk
    
    def dequantize(self, quantized_chunk):
        chunk = self.quantization_step * quantized_chunk
        return chunk


if __name__ == "__main__":
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