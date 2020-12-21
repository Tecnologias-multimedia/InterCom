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
import br_control
import sounddevice as sd

class Spatial_decorrelation(br_control.BR_Control):
    def __init__(self):
        if __debug__:
            print("Running Spatial_decorrelation.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (Spatial_decorrelation) is running")

    # Forward transform:
    #
    #  [w[0]] = [1  1] [x[0]]
    #  [w[1]]   [1 -1] [x[1]]

    def MST_analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1] # L(ow frequency subband)
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1] # H(igh frequency subband)
        return w

    # Inverse transform:
    #
    #  [x[0]] = 1/2 [1  1] [w[0]]
    #  [x[1]]       [1 -1] [w[1]]

    def MST_synthesize(self, w):
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = (w[:, 0] + w[:, 1])/2 # L(ow frequency subband)
        x[:, 1] = (w[:, 0] - w[:, 1])/2 # H(igh frequency subband)
        return x

    def pack(self, chunk_number, chunk)
        analyzed_chunk = self.MST_analyze(chunk)
        return super().pack(chunk_number, analyzed_chunk)

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        synthesize_chunk = self.MST_synthesize(chunk)
        return chunk_number, synthesize_chunk

class Spatial_decorrelation__verbose(Spatial_decorrelation, br_control.BR_Control__verbose):
    def __init__(self):
        if __debug__:
            print("Running Spatial_decorrelation__verbose.__init__")
        super().__init__()
        self.variance = np.zeros(self.NUMBER_OF_CHANNELS) # Variance of the chunks_per_cycle chunks.
        self.entropy = np.zeros(self.NUMBER_OF_CHANNELS) # Entropy of the chunks_per_cycle chunks.
        self.bps = np.zeros(self.NUMBER_OF_CHANNELS) # Bits Per Symbol of the chunks_per_cycle compressed chunks.
        self.chunks_in_the_cycle = []

        self.average_vself, variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_entropy = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_bps = np.zeros(self.NUMBER_OF_CHANNELS)
        
    def stats(self):
        string = super().stats()
        #string += " {}".format(['{:4.1f}'.format(self.quantized_step)])
        return string

    def first_line(self):
        string = super().first_line()
        #string += "{:8s}".format('') # quantized_step
        return string

    def second_line(self):
        string = super().second_line()
        #string += "{:>8s}".format("QS") # quantized_step
        return string

    def separator(self):
        string = super().separator()
        #string += f"{'='*(20)}"
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
        intercom = Spatial_decorrelation__verbose()
    else:
        intercom = Spatial_decorrelation__verbose()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
