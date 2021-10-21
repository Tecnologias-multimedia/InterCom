#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Base class. MST (Mid/Side Transform) is not used.'''

import numpy as np
import minimal
from br_control2 import BR_Control2 as BR_Control
import logging

class Stereo_Coding(BR_Control):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def analyze(self, x):
        return x
 
    def synthesize(self, w):
        return w

    def pack(self, chunk_number, chunk):
        analyzed_chunk = self.analyze(chunk)
        packed_chunk = super().pack(chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = super().unpack(packed_chunk)
        chunk = self.synthesize(analyzed_chunk)
        return chunk_number, chunk

from br_control2 import BR_Control2__verbose as BR_Control__verbose

class Stereo_Coding__verbose(Stereo_Coding, BR_Control__verbose):

    def __init__(self):
        super().__init__()
        self.LH_std_deviation = np.zeros(self.NUMBER_OF_CHANNELS)
        self.average_LH_std_deviation = np.zeros(self.NUMBER_OF_CHANNELS)
        self.LH_chunks_in_the_cycle = []

    def stats(self):
        string = super().stats()
        string += " {}".format(['{:>5d}'.format(int(i/1)) for i in self.LH_std_deviation])
        return string

    def first_line(self):
        string = super().first_line()
        string += "{:19s}".format('') # LH_std_deviation
        return string

    def second_line(self):
        string = super().second_line()
        string += "{:>19s}".format("LH std_deviation") # LH std_deviation
        return string

    def separator(self):
        string = super().separator()
        string += f"{'='*19}"
        return string

    def averages(self):
        string = super().averages()
        string += " {}".format(['{:>5d}'.format(int(i/1)) for i in self.average_LH_std_deviation])
        return string

    def cycle_feedback(self):
        try:
            concatenated_chunks = np.vstack(self.LH_chunks_in_the_cycle)
            self.LH_std_deviation = np.sqrt(np.var(concatenated_chunks, axis=0))
        except ValueError:
            pass
        self.average_LH_std_deviation = self.moving_average(self.average_LH_std_deviation, self.LH_std_deviation, self.cycle)
        super().cycle_feedback()
        self.LH_chunks_in_the_cycle = []

    def analyze(self, chunk):
        analyzed_chunk = super().analyze(chunk)
        self.LH_chunks_in_the_cycle.append(analyzed_chunk)
        return analyzed_chunk

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Stereo_Coding__verbose()
    else:
        intercom = Stereo_Coding()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
