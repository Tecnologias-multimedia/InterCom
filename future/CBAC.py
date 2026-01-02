import pywt
import numpy as np
import math

# ----------------------------
# 1. Generate a synthetic audio signal
# ----------------------------
fs = 16000  # 16 kHz
t = np.linspace(0, 1, fs, endpoint=False)
signal = np.sin(2 * np.pi * 440 * t)  # A4 tone

# ----------------------------
# 2. 1-D DWT
# ----------------------------
wavelet = 'bior4.4'
level = 6
coeffs = pywt.wavedec(signal, wavelet, level=level)
# Flatten coefficients into one array for tree processing
flat_coeffs = np.concatenate(coeffs)
band_sizes = [len(c) for c in coeffs]
band_ids = []
for idx, size in enumerate(band_sizes):
    band_ids.extend([idx] * size)

# ----------------------------
# 3. Dead-zone uniform quantization
# ----------------------------
Q = 10  # quantization step
q_coeffs = np.sign(flat_coeffs) * np.floor(np.abs(flat_coeffs) / Q)
q_coeffs = q_coeffs.astype(int)

# ----------------------------
# 4. Build parent-child tree
# ----------------------------
def build_tree(band_sizes):
    offsets = []
    s = 0
    for n in band_sizes:
        offsets.append(s)
        s += n
    parent = {}
    children = {}
    for level in range(len(band_sizes) - 1):
        for k in range(band_sizes[level]):
            i = offsets[level] + k
            children[i] = []
            for c in (2*k, 2*k+1):
                if c < band_sizes[level+1]:
                    j = offsets[level+1] + c
                    parent[j] = i
                    children[i].append(j)
    roots = list(range(offsets[0], offsets[0]+band_sizes[0]))
    return parent, children, roots

parent, children, roots = build_tree(band_sizes)

# ----------------------------
# 5. Integer arithmetic coder (simplified)
# ----------------------------
class IntArithmeticEncoder:
    def __init__(self):
        self.low = 0
        self.high = (1 << 32) - 1
        self.buffer = []
        self.pending_bits = 0

    def encode_bit(self, bit, p0):
        # simplified
        range_ = self.high - self.low + 1
        split = self.low + int(range_ * p0)
        if bit == 0:
            self.high = split
        else:
            self.low = split + 1
        self._renormalize()

    def encode_integer(self, symbol, cdf):
        range_ = self.high - self.low + 1
        low_p = cdf[symbol]
        high_p = cdf[symbol+1]
        self.high = self.low + int(range_ * high_p / cdf[-1]) - 1
        self.low = self.low + int(range_ * low_p / cdf[-1])
        self._renormalize()

    def _renormalize(self):
        while True:
            if self.high < (1 << 31):
                self._output_bit(0)
            elif self.low >= (1 << 31):
                self._output_bit(1)
                self.low -= (1 << 31)
                self.high -= (1 << 31)
            elif self.low >= (1 << 30) and self.high < (3 << 30):
                self.pending_bits += 1
                self.low -= (1 << 30)
                self.high -= (1 << 30)
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) | 1

    def _output_bit(self, bit):
        self.buffer.append(bit)
        for _ in range(self.pending_bits):
            self.buffer.append(1 - bit)
        self.pending_bits = 0

    def finish(self):
        self.pending_bits += 1
        if self.low < (1 << 30):
            self._output_bit(0)
        else:
            self._output_bit(1)
        return self.buffer

class IntArithmeticDecoder:
    def __init__(self, bitstream):
        self.low = 0
        self.high = (1 << 32) - 1
        self.code = 0
        self.bits = iter(bitstream)
        for _ in range(32):
            self.code = (self.code << 1) | next(self.bits, 0)

    def decode_bit(self, p0):
        range_ = self.high - self.low + 1
        split = self.low + int(range_ * p0)
        if self.code <= split:
            bit = 0
            self.high = split
        else:
            bit = 1
            self.low = split + 1
        self._renormalize()
        return bit

    def decode_integer(self, cdf):
        range_ = self.high - self.low + 1
        total = cdf[-1]
        code_offset = ((self.code - self.low + 1) * total - 1) // range_
        # linear search in CDF
        symbol = next(i for i in range(len(cdf)-1) if cdf[i] <= code_offset < cdf[i+1])
        low_p = cdf[symbol]
        high_p = cdf[symbol+1]
        self.high = self.low + int(range_ * high_p // total) - 1
        self.low = self.low + int(range_ * low_p // total)
        self._renormalize()
        return symbol

    def _renormalize(self):
        while True:
            if self.high < (1 << 31):
                pass
            elif self.low >= (1 << 31):
                self.low -= (1 << 31)
                self.high -= (1 << 31)
                self.code -= (1 << 31)
            elif self.low >= (1 << 30) and self.high < (3 << 30):
                self.low -= (1 << 30)
                self.high -= (1 << 30)
                self.code -= (1 << 30)
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) | next(self.bits, 0)
            self.code = (self.code << 1) | next(self.bits, 0)

# ----------------------------
# 6. Precompute CDFs for magnitude (simple Laplacian approx)
# ----------------------------
max_mag = max(abs(q_coeffs)) + 2
band_lambdas = [0.2 + 0.05*i for i in range(len(band_sizes))]  # example λ per band
cdfs = {}
for b, lam in enumerate(band_lambdas):
    cdf = [0]
    s = 0
    for k in range(1, max_mag + 2):
        p = math.exp(-lam*(k-1))
        s += int(p * 1e6)
        cdf.append(s)
    cdfs[b] = cdf

# ----------------------------
# 7. Encoder
# ----------------------------
def encode_tree(coeffs, band_ids, roots, children, cdfs):
    enc = IntArithmeticEncoder()
    def visit(i, parent_zero):
        is_zero = int(coeffs[i] == 0)
        pz = 0.98 if parent_zero else 0.85
        enc.encode_bit(is_zero, pz)
        if is_zero:
            return
        enc.encode_integer(abs(coeffs[i]), cdfs[band_ids[i]])
        sign = int(coeffs[i] < 0)
        enc.encode_bit(sign, 0.5)
        for j in children.get(i, []):
            visit(j, False)
    for r in roots:
        visit(r, False)
    return enc.finish()

bitstream = encode_tree(q_coeffs, band_ids, roots, children, cdfs)
print("Encoded bitstream length:", len(bitstream))

# ----------------------------
# 8. Decoder
# ----------------------------
def decode_tree(bitstream, band_ids, roots, children, cdfs):
    dec = IntArithmeticDecoder(bitstream)
    coeffs = {}
    def visit(i, parent_zero):
        pz = 0.98 if parent_zero else 0.85
        is_zero = dec.decode_bit(pz)
        if is_zero:
            coeffs[i] = 0
            return
        mag = dec.decode_integer(cdfs[band_ids[i]])
        sign = dec.decode_bit(0.5)
        coeffs[i] = -mag if sign else mag
        for j in children.get(i, []):
            visit(j, False)
    for r in roots:
        visit(r, False)
    # convert to array in original order
    return np.array([coeffs[i] for i in range(len(band_ids))])

decoded_q_coeffs = decode_tree(bitstream, band_ids, roots, children, cdfs)

# ----------------------------
# 9. Verify correctness
# ----------------------------
assert np.array_equal(q_coeffs, decoded_q_coeffs)
print("Decoding successful: quantized coefficients match exactly!")
