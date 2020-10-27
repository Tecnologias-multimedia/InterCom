"""Shows subband gains (energy of a coefficient in the inverse DWT)
for a givel wavelet and plots the basis functions.

"""

import argparse
import matplotlib.pyplot as plt
import numpy as np
import pywt as wt

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument( '-b', '--block_size', type=int, default=512,
                     help='block size (in samples/coefficients)')
parser.add_argument( '-s', '--skip', type=int, default=16,
                     help='number of skipped basis fuctions')
parser.add_argument( '-v', '--levels', type=int, default=5,
                     help='number of levels of the DWT')
parser.add_argument( '-w', '--wavelet', type=str, default="db5",
                     help=f'wavelet name from {wt.wavelist()}')
parser.add_argument( '-p', '--padding', type=str,
                     default="periodization",
                     help=f'signal extension procedure from {wt.Modes.modes}')
args = parser.parse_args()

# Get the number of wavelet coefficients to get the number of samples
#shapes = wt.wavedecn_shapes((samples,), wavelet)

# Energy of the signal x
def energy(x):
    return np.sum(x*x)/len(x)

# Stuff for the axis
sample = np.arange(0, args.block_size, 1)
fig, axs = plt.subplots(args.block_size//args.skip, 1, sharex=True)
for i in range(0,args.block_size,args.skip):
    axs[i//args.skip].set_ylim(-args.block_size, args.block_size)
    axs[i//args.skip].grid(True)
axs[args.block_size//args.skip-1].set_xlabel('sample')
axs[args.block_size//args.skip//2].set_ylabel('amplitude')

print("Coefficient\t   Energy")


zeros = np.zeros(args.block_size)
coeffs = wt.wavedec(zeros, wavelet=args.wavelet, level=args.levels,
                    mode=args.padding)
arr, coeff_slices = wt.coeffs_to_array(coeffs)
for i in range(0,args.block_size,args.skip):
    
    # The basis functions are created by computing the inverse DWt of
    # an DWT spectrum where all coefficients are zero except one of
    # them. Depending on the position of such coefficient, a different
    # basis function is obtained.
    
    arr[i] = args.block_size # i is the coeff different from 0
    coeffs_from_arr = wt.array_to_coeffs(arr, coeff_slices,
                                         output_format="wavedec")
    samples = wt.waverec(coeffs_from_arr, wavelet=args.wavelet,
                         mode=args.padding)
    arr[i] = 0
    print("       %4d" % i, "\t", "%8.2f" % energy(samples))
    axs[i//args.skip].plot(sample, samples)

plt.show()

