#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (compress3.py). '''

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
import compress3

class Compression4(compress3.Compression3):
    '''Compress the chunks by byte-planes ([MSB], [LSB]), where the frames
are interlaced [frame0, frame1](. Each byte-plane is compressed
independently.

    '''
    def __init__(self):
        if __debug__:
            print("Running Compression4.__init__")
        super().__init__()
        if __debug__:
            print("InterCom (Compression4) is running")

    # To write ...

class Compression3__verbose(Compression3, compress2.Compression2__verbose):
    pass

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
        intercom = Compression4__verbose()
    else:
        intercom = Compression4()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
