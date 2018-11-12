# PyAudio to capture and broadcast audio
import pyaudio
# NumPy to change variable types
import numpy as np
# Pywt to calculate Discrete Wavelet Transform (DWT)
import pywt
# SciPy to calculate entropy
import scipy.stats as st


# Declaration of variables
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()

# Variable that we use to capture and broadcast audio
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
                frames_per_buffer=CHUNK)


# Calculate the histogram in int16 number from the array passed
# by parameter
def histogram(array):
      return np.histogram(array.astype(np.int16),
                        bins=np.arange(65536))


# Main
def main():
      i = 0
      while True:
            i = i+1
            # Read from the sound card Chunk to CHUNK
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Pass from type bytes to int16 using the numpy library
            array_In = np.frombuffer(data, dtype=np.int16)
            # Print the results on the screen
            histIn, bin_edges = histogram(array_In)
            print('Input ', i, ' --> Max:', max(array_In),
                  ', Min:', min(array_In),
                  ', Entropy:', st.entropy(histIn))
            # Calculate the transform and store it in six arrays
            # in floating point64
            coeffs = pywt.wavedec(array_In, 'db1', level=5)
            cA5, cD5, cD4, cD3, cD2, cD1 = coeffs
            # Calculate the histogram of all components
            histcA5, bin_edges = histogram(cA5)
            histcD5, bin_edges = histogram(cD5)
            histcD4, bin_edges = histogram(cD4)
            histcD3, bin_edges = histogram(cD3)
            histcD2, bin_edges = histogram(cD2)
            histcD1, bin_edges = histogram(cD1)                  
            # Sum all histograms calculated
            hist_sum =  (histcA5 + histcD5 + histcD4 + histcD3 + 
                        histcD2 + histcD1)
            hist_sum = np.ndarray([65536,1], dtype=np.int16, 
                              buffer=hist_sum)
            # Print the results on the screen
            print('Transformed ', i, '--> Max:', max(max(
                  cA5.astype(np.int16)),max(cD5.astype(np.int16)),
                  max(cD4.astype(np.int16)),max(cD3.astype(np.int16)),
                  max(cD2.astype(np.int16)),max(cD1.astype(np.int16))),
                  ', Min:', min(min(
                  cA5.astype(np.int16)),min(cD5.astype(np.int16)),
                  min(cD4.astype(np.int16)),min(cD3.astype(np.int16)),min(cD2.astype(np.int16)),min(cD1.astype(np.int16))),
                  ', Entropy:', st.entropy(hist_sum)[0])
            # Calculate the inverse transform and store as int16
            # with the numpy library
            array_Out = pywt.waverec(coeffs, 'db1').astype(np.int16)
            # Print the results on the screen
            histOut, bin_edges = histogram(array_Out)
            print('Output ', i, ' --> Max:', max(array_Out),
                  ', Min:', min(array_Out),
                  ', Entropy:', st.entropy(histOut))
            # Transmit from the sound card the wavelet array casted
            # to bytes
            stream.write(array_Out.tobytes())


if __name__ == '__main__':
    main()
