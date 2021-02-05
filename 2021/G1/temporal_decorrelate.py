from stereo_decorrelate import Stereo_decorrelation
import numpy as np
import pywt

class Temporal_decorrelation(Stereo_decorrelation):
    def __init__(self, wavelet="db20", levels=5):
        self.wavelet = pywt.Wavelet(wavelet)
        self.levels = levels
        self.slices = None
        self.shapes = None
        self.size = None
        #self.slices = [(slice(None, 64, None),), {'d': (slice(64, 128, None),)}, {'d': (slice(128, 256, None),)}, {'d': (slice(256, 512, None),)}, {'d': (slice(512, 1024, None),)}]
        #self.shapes = [(32,), {'d': (32,)}, {'d': (64,)}, {'d': (128,)}, {'d': (256,)}, {'d': (512,)}]

    def DWT_analyze(self, x, level=None, wavelet=None):
        if level is None:
            level = self.levels
        if wavelet is None:
            wavelet = self.wavelet

        decomposition_0 = pywt.wavedec(x[:, 0], wavelet=wavelet, level=level, mode="per")
        decomposition_1 = pywt.wavedec(x[:, 1], wavelet=wavelet, level=level, mode="per")
        coefs_0, slices, shapes = pywt.ravel_coeffs(decomposition_0)
        
        if self.slices is None:
            self.slices = slices
        if self.shapes is None:
            self.shapes = shapes
        if self.size is None:
            self.size = len(coefs_0)

        coefs_1, _, _ = pywt.ravel_coeffs(decomposition_1)
        coefs_0 = np.rint(coefs_0).astype(np.int32)
        coefs_1 = np.rint(coefs_1).astype(np.int32)
        return np.concatenate((coefs_0, coefs_1))

    def DWT_synthesize(self, coefs, wavelet=None):
        if wavelet is None:
            wavelet = self.wavelet

        samples = np.empty((self.size, 2), dtype=np.int16)
        decomposition_0 = pywt.unravel_coeffs(coefs[:self.size], self.slices, self.shapes, output_format="wavedec")
        decomposition_1 = pywt.unravel_coeffs(coefs[self.size:], self.slices, self.shapes, output_format="wavedec")
        samples[:, 0] = np.rint(pywt.waverec(decomposition_0, wavelet=wavelet, mode="per")).astype(np.int16)
        samples[:, 1] = np.rint(pywt.waverec(decomposition_1, wavelet=wavelet, mode="per")).astype(np.int16)
        return samples