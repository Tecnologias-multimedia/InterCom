import numpy as np
import math
import threading
import time
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import minimal
import buffer
import compress
import br_control

class Spatial_decorrelation(br_control.BR_Control):
    
    def __init__(self):
        if __debug__:
            print("Running BR_Control.__init__")
        super().__init__()
    
    def pack(self, chunk_number, chunk):
        analyzed_chunk = self.MST_analyze(chunk)
        packed_chunk = super().pack(chunk_number, analyzed_chunk)
        print("SP:", len(chunk)/len(packed_chunk))
        return packed_chunk
    
    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, analyzed_chunk = super().unpack(packed_chunk, dtype)
        chunk = self.MST_synthesize(analyzed_chunk)
        return chunk_number, chunk
    
    def MST_analyze(self,chunk):
        analyzed_chunk = np.empty_like(chunk, dtype=np.int32)
        analyzed_chunk[:, 0] = chunk[:, 0].astype(np.int32) + chunk[:, 1] # L(ow frequency subband)
        analyzed_chunk[:, 1] = chunk[:, 0].astype(np.int32) - chunk[:, 1] # H(igh frequency subband)
        return analyzed_chunk
    
    def MST_synthesize(self,analyzed_chunk):
        chunk = np.empty_like(analyzed_chunk, dtype=np.int16)
        chunk[:, 0] = (analyzed_chunk[:, 0] + analyzed_chunk[:, 1])/2 # L(ow frequency subband)
        chunk[:, 1] = (analyzed_chunk[:, 0] - analyzed_chunk[:, 1])/2 # H(igh frequency subband)
        return chunk
    
if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_args()
    intercom = Spatial_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
