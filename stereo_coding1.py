#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Real-time Audio Intercommunicator (stereo_coding1.py).'''

import numpy as np
import minimal
import stereo_coding

class Stereo_Coding1(stereo_coding.Stereo_Coding):
    '''Implements MST for 32 bits/coefficient output. Thought for using
after temporal_coding, where 32 bits/coefficient are required.'''

    def __init__(self):
        if __debug__:
            print("Running Stereo_Coding1.__init__")
        super().__init__()

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

class Stereo_Coding1__verbose(Stereo_Coding1, stereo_coding.Stereo_Coding__verbose):
    def __init__(self):
        if __debug__:
            print("Running Stereo_Coding0__verbose.__init__")
        super().__init__()

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

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
        intercom = Stereo_Coding1__verbose()
    else:
        intercom = Stereo_Coding1()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
