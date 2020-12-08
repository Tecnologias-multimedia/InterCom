import zlib
import numpy as np
import struct
import math
from multiprocessing import Process
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import buffer
import compress
import psutil

class BR_Control(compress.Compression):
    def __init__(self):
        super().__init__()
        self.quantization_step = 1
        #self.br = 0
        #self.braux = 0
        #print("Br, Q")
        #Process(target=self.q_balance).start()
    
    def q_balance(self):
        self.br = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
        self.quantization_step = (int) ((1-(-1))/(2**(self.br/minimal.args.frames_per_second)))
    
    def entropy_in_bits_per_symbol(self, sequence_of_symbols):
        value, counts = np.unique(sequence_of_symbols, return_counts = True)
        probs = counts / len(sequence_of_symbols)
        n_classes = np.count_nonzero(probs)
        
        if n_classes >= 1:
            return 0
        
        entropy = 0
        for i in probs:
            entropy -= i*math.log(i, 2)
        
        return entropy
    
    def pack(self, chunk_number, chunk):
        #self.br = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv - self.braux
        #self.quantization_step = (int) ((1-(-1))/(2**(int)(self.br/minimal.args.frames_per_second)))
        #if self.quantization_step==0:
        #    self.quantization=1
        
        #quantize(chunk)
        quantized_chunk = self.quantize(chunk)
        ##self.br = self.entropy_in_bits_per_symbol(quantized_chunk)
        #print(self.br, self.quantization_step)
        
        #Compression.pack()
        packed_chunk = buffer.Buffering.pack(self,chunk_number,chunk)
        #self.braux = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
        return packed_chunk
    
    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        #Compression.unpack()
        chunk_number,quantized_chunk = buffer.Buffering.unpack(self,packed_chunk, dtype)
        #dequantize(quantized_chunk)
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