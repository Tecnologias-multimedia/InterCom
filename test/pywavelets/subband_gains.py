# Plots the basis functions of a wavelet transform and computes the
# energy of each of one of such functions.

import matplotlib.pyplot as plt
import numpy as np
import pywt as wt

# Number of skipped basis functions
skip = 16

# Number of samples to synthesize
number_of_samples = 512

# Number of levels of the DWT
levels = 4

# Wavelet used
#wavelet = 'haar'
#wavelet = 'bior1.3'
#wavelet = 'bior1.5'
#wavelet = 'bior3.3'
wavelet = 'bior3.5'
#wavelet = 'rbio1.3'
#wavelet = 'rbio3.5'
#wavelet = "db5"
#wavelet = "coif3"
#wavelet = "dmey"

#padding = "symmetric"
padding = "periodization"

# Get the number of wavelet coefficients to get the number of samples
#shapes = wt.wavedecn_shapes((samples,), wavelet)

# Energy of the signal x
def energy(x):
    return np.sum(x*x)/len(x)

# Stuff for the axis
sample = np.arange(0, number_of_samples, 1)
fig, axs = plt.subplots(number_of_samples//skip, 1, sharex=True)
for i in range(0,number_of_samples,skip):
    axs[i//skip].set_ylim(-number_of_samples, number_of_samples)
    axs[i//skip].grid(True)
axs[number_of_samples//skip-1].set_xlabel('sample')
axs[number_of_samples//skip//2].set_ylabel('amplitude')

print("Coefficient\t   Energy")

for i in range(0,number_of_samples,skip):
    
    # The basis functions are created by computing the inverse DWt of
    # an DWT spectrum where all coefficients are zero except one of
    # them. Depending on the position of such coefficient, a different
    # basis function is obtained.
    zeros = np.zeros(number_of_samples)
    coeffs = wt.wavedec(zeros, wavelet=wavelet, level=levels, mode=padding)
    arr, coeff_slices = wt.coeffs_to_array(coeffs)
    arr[i] = number_of_samples # i is the coeff different of 0
    coeffs_from_arr = wt.array_to_coeffs(arr, coeff_slices, output_format="wavedec")
    samples = wt.waverec(coeffs_from_arr, wavelet=wavelet, mode=padding)
    print("       %4d" % i, "\t", "%8.2f" % energy(samples))
    axs[i//skip].plot(sample, samples)

plt.show()

