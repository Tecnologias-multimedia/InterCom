#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''MST using 32 bits/coefficient.'''

import numpy as np
import logging

import minimal
import stereo_MST_coding_16

class Stereo_MST_Coding_32(stereo_MST_coding_16.Stereo_MST_Coding_16):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1]
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1]
        return w
 
    def synthesize(self, w):
        x = np.empty_like(w)
        x[:, 0] = (w[:, 0] + w[:, 1])/2
        x[:, 1] = (w[:, 0] - w[:, 1])/2
        return x

class Stereo_MST_Coding_32__verbose(Stereo_MST_Coding_32, stereo_MST_coding_16.Stereo_MST_Coding_16__verbose):
    pass
'''
    def __init__(self):
        super().__init__()

    def analyze(self, chunk):
        analyzed_chunk = Stereo_MST_Coding_32.analyze(self, chunk)
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
        intercom = Stereo_MST_Coding_32__verbose()
    else:
        intercom = Stereo_MST_Coding_32()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
