#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (temporal_coding0.py). '''

import minimal
from compress2 import Compression2 as Compression
from br_control2 import BR_Control2 as BR_Control 
from stereo_coding1 import Stereo_Coding1 as Stereo_Coding
from temporal_coding import Temporal_Coding

class Temporal_Coding0(Temporal_Coding):
    '''Removes first intra-frame redudancy and then, intra-channel redundancy.

    '''
    def __init__(self):
        if __debug__:
            print("Running Temporal_Coding0.__init__")
        super().__init__()

    def pack(self, chunk_number, chunk):
        chunk = Stereo_Coding.analyze(self, chunk)
        chunk = super().analyze(chunk)
        quantized_chunk = BR_Control.quantize(self, chunk)
        compressed_chunk = Compression.pack(self, chunk_number, quantized_chunk)
        return compressed_chunk

    def unpack(self, compressed_chunk):
        chunk_number, quantized_chunk = Compression.unpack(self, compressed_chunk)
        chunk = BR_Control.dequantize(self, quantized_chunk)
        chunk = super().synthesize(chunk)
        chunk = Stereo_Coding.synthesize(self, chunk)
        return chunk_number, chunk

from temporal_coding import Temporal_Coding__verbose

class Temporal_Coding0__verbose(Temporal_Coding0, Temporal_Coding__verbose):
    ''' Verbose version of Decorrelation. '''
    pass

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
        intercom = Temporal_Coding0__verbose()
    else:
        intercom = Temporal_Coding0()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
