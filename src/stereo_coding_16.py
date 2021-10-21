#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Implements MST using 16 bits/coefficient.'''

import numpy as np
import minimal
import stereo_coding
import logging

class Stereo_Coding_16(stereo_coding.Stereo_Coding):

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

class Stereo_Coding_16__verbose(Stereo_Coding_16, stereo_coding.Stereo_Coding__verbose):

    def __init__(self):
        super().__init__()

    def _analyze(self, x):
        return stereo_coding.Stereo_Coding__verbose.analyze(self, x)
    def analyze(self, chunk):
        analyzed_chunk = Stereo_Coding_16.analyze(self, chunk)
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
        intercom = Stereo_Coding_16__verbose()
    else:
        intercom = Stereo_Coding_16()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
