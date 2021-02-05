import numpy as np
from br_control import Quantization 

class Stereo_decorrelation(Quantization):
    def __init__(self):
        pass

    def MST_analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1] # L(ow frequency subband)
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1] # H(igh frequency subband)
        return w

    def MST_synthesize(self, w):
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = (w[:, 0] + w[:, 1])/2 # L(ow frequency subband)
        x[:, 1] = (w[:, 0] - w[:, 1])/2 # H(igh frequency subband)
        return x