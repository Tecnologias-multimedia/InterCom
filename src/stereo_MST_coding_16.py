#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''MST using 16 bits/coefficient.'''

import numpy as np
import logging

import minimal
from BR_control_conservative import BR_Control_Conservative as BR_Control

class Stereo_MST_Coding_16(BR_Control):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def analyze(self, x):
        #w = np.empty_like(x, dtype=np.int32)
        w = np.empty_like(x, dtype=np.int16)
        #w[:, 0] = (x[:, 0].astype(np.int32) + x[:, 1])/2
        w[:, 0] = (x[:, 0].astype(np.int32) + x[:, 1])/2
        #w[:, 1] = (x[:, 0].astype(np.int32) - x[:, 1])/2
        w[:, 1] = (x[:, 0].astype(np.int32) - x[:, 1])/2
        return w
 
    def synthesize(self, w):
        #x = np.empty_like(w)
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = w[:, 0] + w[:, 1]
        x[:, 1] = w[:, 0] - w[:, 1]
        return x

    def pack(self, chunk_number, chunk):
        analyzed_chunk = self.analyze(chunk)
        packed_chunk = super().pack(chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = super().unpack(packed_chunk)
        chunk = self.synthesize(analyzed_chunk)
        return chunk_number, chunk

from BR_control_add_lost import BR_Control_Add_Lost__verbose as BR_Control__verbose

class Stereo_MST_Coding_16__verbose(Stereo_MST_Coding_16, BR_Control__verbose):
    pass
'''
    def __init__(self):
        super().__init__()

    def analyze(self, chunk):
        analyzed_chunk = Stereo_MST_Coding_16.analyze(self, chunk)
        self.LH_chunks_in_the_cycle.append(analyzed_chunk)
        return analyzed_chunk
'''

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
        intercom = Stereo_MST_Coding_16__verbose()
    else:
        intercom = Stereo_MST_Coding_16()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
