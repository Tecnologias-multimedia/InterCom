#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Overlapping DWT processing.'''

import numpy as np
import pywt
import logging

import minimal
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT

class Temporal_Overlapped_DWT(Temporal_No_Overlapped_DWT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        chunk_list = []
        chunk_list.append(self.generate_zero_chunk())
        chunk_list.append(self.generate_zero_chunk())
        chunk_list.append(self.generate_zero_chunk())

    def analyze(self, chunk):
        return super().analyze(chunk)

    def synthesize(self, chunk_DWT):
        return super().synthesize(chunk_DWT)

from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT__verbose

class Temporal_Overlapped_DWT__verbose(Temporal_No_Overlapped_DWT__verbose):
    pass

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
        intercom = Temporal_Overlapped_DWT__verbose()
    else:
        intercom = Temporal_Overlapped_DWT()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
