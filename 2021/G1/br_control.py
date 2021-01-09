import numpy as np

class Quantization():
    def __init__(self):
        pass

    def quantize(self, chunk, quantization_step):
        """Chunk quantification
            """
        return (chunk/quantization_step).astype(np.int32)
        
    def dequantize(self, chunk, dequantization_step):
        """Chunk dequantization
            """
        return chunk*dequantization_step