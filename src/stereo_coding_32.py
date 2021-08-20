#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Implements MST (Mid/Side Transform) for 32 bits/coefficients.'''
import numpy as np
import minimal
import stereo_coding
import logging

class Stereo_Coding_32(stereo_coding.Stereo_Coding):

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

class Stereo_Coding_32__verbose(Stereo_Coding_32, stereo_coding.Stereo_Coding__verbose):

    def __init__(self):
        if __debug__:
            print("Running Stereo_Coding0__verbose.__init__")
        super().__init__()

    def analyze(self, x):
        return stereo_coding.Stereo_Coding__verbose.analyze(self, x)

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
        intercom = Stereo_Coding_32__verbose()
    else:
        intercom = Stereo_Coding_32()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
