#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Real-time Audio Intercommunicator (removes inter-channel redundancy).
'''

import numpy as np
import sounddevice as sd
import math
import struct
import zlib
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import buffer
import compress
import br_control

class Intra_frame_decorrelation(br_control.BR_Control):
    ''' Removes the inter-channel (spatial).
    '''

    def __init__(self):
        if __debug__:
            print("Running Intra_frame_decorrelation.__init__")
        super().__init__()

    def analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1]
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1]
        return w

    def synthesize(self, w):
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = (w[:, 0] + w[:, 1])/2
        x[:, 1] = (w[:, 0] - w[:, 1])/2
        return x

    def pack(self, chunk_number, chunk):
        '''Removes stereo redundancy.'''
        analyzed_chunk = self.analyze(chunk)
        packed_chunk = super().pack(chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        '''Restores the original chunk representation.'''
        chunk_number, analyzed_chunk = super().unpack(packed_chunk, dtype)
        chunk = self.synthesize(analyzed_chunk)
        return chunk_number, chunk

class Intra_frame_decorrelation__verbose(Intra_frame_decorrelation, br_control.BR_Control__verbose):
    def __init__(self):
        super().__init__()
        self.LH_variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_LH_variance = np.zeros(self.NUMBER_OF_CHANNELS)
        self.LH_chunks_in_the_cycle = []

    def stats(self):
        string = super().stats()
        string += " {}".format(['{:>5d}'.format(int(i/1000)) for i in self.LH_variance])
        return string

    def _first_line(self):
        string = super().first_line()
        string += "{:19s}".format('') # LH_variance
        return string

    def first_line(self):
        string = super().first_line()
        string += "{:19s}".format('') # LH_variance
        return string

    def second_line(self):
        string = super().second_line()
        string += "{:>19s}".format("LH variance") # LH variance
        return string

    def separator(self):
        string = super().separator()
        string += f"{'='*19}"
        return string

    def averages(self):
        string = super().averages()
        string += " {}".format(['{:>5d}'.format(int(i/1000)) for i in self.average_LH_variance])
        return string

    def cycle_feedback(self):
        try:
            concatenated_chunks = np.vstack(self.LH_chunks_in_the_cycle)
            self.LH_variance = np.var(concatenated_chunks, axis=0)
        except ValueError:
            pass
        self.average_LH_variance = self.moving_average(self.average_LH_variance, self.LH_variance, self.cycle)
        super().cycle_feedback()
        self.LH_chunks_in_the_cycle = []

    def analyze(self, chunk):
        analyzed_chunk = super().analyze(chunk)
        self.LH_chunks_in_the_cycle.append(analyzed_chunk)
        return analyzed_chunk

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
        intercom = Intra_frame_decorrelation__verbose()
    else:
        intercom = Intra_frame_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
