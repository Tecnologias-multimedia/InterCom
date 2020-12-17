import numpy as np
import br_control
import minimal
import sys
class Spatial_decorrelation(br_control.BR_Control__verbose):
    
    def pack(self, chunk_number, chunk):
        w = self.MST_analyze(chunk)
        packed_chunk = super().pack(chunk_number, w)
        return packed_chunk
    
    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        chunk_number, analyzed_chunk = super().unpack(packed_chunk, dtype)
        x = self.MST_synthesize(analyzed_chunk)
        return chunk_number, x
    
    def MST_analyze(self,chunk):
        w = np.empty_like(chunk, dtype=np.int32)
        w[:, 0] = chunk[:, 0].astype(np.int32) + chunk[:, 1]
        w[:, 1] = chunk[:, 0].astype(np.int32) - chunk[:, 1] 
        return w
    
    def MST_synthesize(self,chunk):
        x = np.empty_like(chunk, dtype=np.int16)
        x[:, 0] = (chunk[:, 0] + chunk[:, 1])/2 
        x[:, 1] = (chunk[:, 0] - chunk[:, 1])/2 
        return x
    
if __name__ == "__main__":
    minimal.parser.description = __doc__
    minimal.args = minimal.parser.parse_args()
    intercom = Spatial_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
