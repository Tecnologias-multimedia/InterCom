import pywt
import numpy as np
import math

# ----------------------------
# 1. Generate synthetic audio signal
# ----------------------------
fs = 16000
t = np.linspace(0, 1, fs, endpoint=False)
signal = np.sin(2 * np.pi * 440 * t)

# ----------------------------
# 2. 1-D DWT
# ----------------------------
wavelet = 'bior4.4'
level = 6
coeffs = pywt.wavedec(signal, wavelet, level=level)
flat_coeffs = np.concatenate(coeffs)
band_sizes = [len(c) for c in coeffs]
band_ids = []
for idx, size in enumerate(band_sizes):
    band_ids.extend([idx]*size)

# ----------------------------
# 3. Dead-zone uniform quantization
# ----------------------------
Q = 10
q_coeffs = np.sign(flat_coeffs) * np.floor(np.abs(flat_coeffs)/Q)
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
    for level in range(len(band_sizes)-1):
        for k in range(band_sizes[level]):
            i = offsets[level]+k
            children[i] = []
            for c in (2*k, 2*k+1):
                if c < band_sizes[level+1]:
                    j = offsets[level+1]+c
                    parent[j] = i
                    children[i].append(j)
    roots = list(range(offsets[0], offsets[0]+band_sizes[0]))
    return parent, children, roots

parent, children, roots = build_tree(band_sizes)

# ----------------------------
# 5. Integer arithmetic coder
# ----------------------------
class IntArithmeticEncoder:
    def __init__(self):
        self.low = 0
        self.high = (1<<32)-1
        self.buffer = []
        self.pending_bits = 0
    def encode_bit(self, bit, p0):
        range_ = self.high - self.low + 1
        split = self.low + int(range_ * p0)
        if bit==0: self.high=split
        else: self.low=split+1
        self._renormalize()
    def encode_integer(self, symbol, cdf):
        range_ = self.high - self.low + 1
        low_p = cdf[symbol]
        high_p = cdf[symbol+1]
        self.high = self.low + int(range_*high_p/cdf[-1])-1
        self.low = self.low + int(range_*low_p/cdf[-1])
        self._renormalize()
    def _renormalize(self):
        while True:
            if self.high < (1<<31):
                self._output_bit(0)
            elif self.low >= (1<<31):
                self._output_bit(1)
                self.low -= (1<<31)
                self.high -= (1<<31)
            elif self.low >= (1<<30) and self.high < (3<<30):
                self.pending_bits += 1
                self.low -= (1<<30)
                self.high -= (1<<30)
            else: break
            self.low <<= 1
            self.high = (self.high << 1)|1
    def _output_bit(self, bit):
        self.buffer.append(bit)
        for _ in range(self.pending_bits):
            self.buffer.append(1-bit)
        self.pending_bits=0
    def finish(self):
        self.pending_bits += 1
        if self.low < (1<<30): self._output_bit(0)
        else: self._output_bit(1)
        return self.buffer

class IntArithmeticDecoder:
    def __init__(self, bitstream):
        self.low=0
        self.high=(1<<32)-1
        self.code=0
        self.bits=iter(bitstream)
        for _ in range(32): self.code=(self.code<<1)|next(self.bits,0)
    def decode_bit(self,p0):
        range_=self.high-self.low+1
        split=self.low+int(range_*p0)
        if self.code <= split: bit=0; self.high=split
        else: bit=1; self.low=split+1
        self._renormalize()
        return bit
    def decode_integer(self,cdf):
        range_=self.high-self.low+1
        total=cdf[-1]
        code_offset=((self.code-self.low+1)*total-1)//range_
        symbol = next(i for i in range(len(cdf)-1) if cdf[i]<=code_offset<cdf[i+1])
        low_p=cdf[symbol]; high_p=cdf[symbol+1]
        self.high=self.low+int(range_*high_p//total)-1
        self.low=self.low+int(range_*low_p//total)
        self._renormalize()
        return symbol
    def _renormalize(self):
        while True:
            if self.high<(1<<31): pass
            elif self.low>=(1<<31): self.low-=1<<31; self.high-=1<<31; self.code-=1<<31
            elif self.low>=(1<<30) and self.high<(3<<30): self.low-=1<<30; self.high-=1<<30; self.code-=1<<30
            else: break
            self.low<<=1; self.high=(self.high<<1)|1
            self.code=(self.code<<1)|next(self.bits,0)

# ----------------------------
# 6. Subband-adaptive α and λ
# ----------------------------
# α: child prediction factor per band
subband_alpha = [0.8] + [0.5+0.05*i for i in range(1,len(band_sizes))]  
# λ: Laplacian parameter per band
subband_lambda = [0.15] + [0.2+0.05*i for i in range(1,len(band_sizes))]

# Precompute CDFs for residuals per band
max_mag = max(abs(q_coeffs))+2
cdfs = {}
for b, lam in enumerate(subband_lambda):
    cdf=[0]; s=0
    for k in range(0,max_mag+2):
        p=math.exp(-lam*k)
        s+=int(p*1e6)
        cdf.append(s)
    cdfs[b]=cdf

# ----------------------------
# 7. Encoder with subband-adaptive prediction
# ----------------------------
def encode_tree_subband(coeffs, band_ids, roots, children, cdfs, alpha_list):
    enc=IntArithmeticEncoder()
    def visit(i,parent_zero,parent_mag=0):
        is_zero=int(coeffs[i]==0)
        pz=0.98 if parent_zero else 0.85
        enc.encode_bit(is_zero,pz)
        if is_zero: return
        alpha=alpha_list[band_ids[i]]
        pred=int(round(alpha*parent_mag)) if parent_mag>0 else 0
        residual=max(abs(coeffs[i])-pred,0)
        enc.encode_integer(residual,cdfs[band_ids[i]])
        sign=int(coeffs[i]<0)
        enc.encode_bit(sign,0.5)
        for j in children.get(i,[]):
            visit(j,parent_zero=False,parent_mag=abs(coeffs[i]))
    for r in roots: visit(r,parent_zero=False,parent_mag=0)
    return enc.finish()

bitstream=encode_tree_subband(q_coeffs,band_ids,roots,children,cdfs,subband_alpha)
print("Encoded bitstream length:",len(bitstream))

# ----------------------------
# 8. Decoder with subband-adaptive prediction
# ----------------------------
def decode_tree_subband(bitstream, band_ids, roots, children, cdfs, alpha_list):
    dec=IntArithmeticDecoder(bitstream)
    coeffs={}
    def visit(i,parent_zero,parent_mag=0):
        pz=0.98 if parent_zero else 0.85
        is_zero=dec.decode_bit(pz)
        if is_zero: coeffs[i]=0; return
        alpha=alpha_list[band_ids[i]]
        pred=int(round(alpha*parent_mag)) if parent_mag>0 else 0
        residual=dec.decode_integer(cdfs[band_ids[i]])
        mag=pred+residual
        sign=dec.decode_bit(0.5)
        coeffs[i]=-mag if sign else mag
        for j in children.get(i,[]):
            visit(j,parent_zero=False,parent_mag=mag)
    for r in roots: visit(r,parent_zero=False,parent_mag=0)
    return np.array([coeffs[i] for i in range(len(band_ids))])

decoded_q_coeffs=decode_tree_subband(bitstream,band_ids,roots,children,cdfs,subband_alpha)
assert np.array_equal(q_coeffs,decoded_q_coeffs)
print("Decoding successful!")

# ----------------------------
# 9. Inverse DWT reconstruction
# ----------------------------
reconstructed_coeffs=[]
idx=0
for size in band_sizes:
    reconstructed_coeffs.append(decoded_q_coeffs[idx:idx+size].astype(float)*Q)
    idx+=size

reconstructed_signal=pywt.waverec(reconstructed_coeffs,wavelet)
reconstructed_signal=reconstructed_signal[:len(signal)]

# ----------------------------
# 10. Compute SNR / PSNR
# ----------------------------
mse=np.mean((signal-reconstructed_signal)**2)
signal_power=np.mean(signal**2)
snr=10*np.log10(signal_power/mse)
psnr=10*np.log10(np.max(signal)**2/mse)
print(f"SNR: {snr:.2f} dB")
print(f"PSNR: {psnr:.2f} dB")
