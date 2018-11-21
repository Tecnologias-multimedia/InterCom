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


# Function that a component passes in 32-bit planes assigned to a list
def array_to_planos(planos):
      b = planos.astype(np.int32)
      c = [(b & (0b1<<31)) >> 31,(b & (0b1<<30)) >> 30, (b & (0b1<<29)) >> 29, (b & (0b1<<28)) >> 28
            , (b & (0b1<<27)) >> 27, (b & (0b1<<26)) >> 26, (b & (0b1<<25)) >> 25, (b & (0b1<<24)) >> 24
            , (b & (0b1<<23)) >> 23, (b & (0b1<<22)) >> 22, (b & (0b1<<21)) >> 21, (b & (0b1<<20)) >> 20
            , (b & (0b1<<19)) >> 19, (b & (0b1<<18)) >> 18, (b & (0b1<<17)) >> 17, (b & (0b1<<16)) >> 16
            , (b & (0b1<<15)) >> 15, (b & (0b1<<14)) >> 14, (b & (0b1<<13)) >> 13, (b & (0b1<<12)) >> 12
            , (b & (0b1<<11)) >> 11, (b & (0b1<<10)) >> 10, (b & (0b1<<9)) >> 9, (b & (0b1<<8)) >> 8
            , (b & (0b1<<7)) >> 7, (b & (0b1<<6)) >> 6, (b & (0b1<<5)) >> 5, (b & (0b1<<4)) >> 4
            , (b & (0b1<<3)) >> 3, (b & (0b1<<2)) >> 2, (b & (0b1<<1)) >> 1, (b & (0b1<<0)) >> 0]
      return c


# Function that passes the list of 32 bits to decimal array
def planos_to_array(plano):
      var1 = (plano[0]<<31 | plano[1]<<30 | plano[2]<<29 | plano[3]<<28 | plano[4]<<27 | plano[5]<<26 | plano[6]<<25 | 
            plano[7]<<24 | plano[8]<<23 | plano[9]<<22 | plano[10]<<21 | plano[11]<<20 | plano[12]<<19 | plano[13]<<18 | 
            plano[14]<<17 | plano[15]<<16 | plano[16]<<15 | plano[17]<<14 | plano[18]<<13 | plano[19]<<12 | plano[20]<<11 | 
            plano[21]<<10 | plano[22]<<9 | plano[23]<<8 | plano[24]<<7 | plano[25]<<6 | plano[26]<<5 | plano[27]<<4 | 
            plano[28]<<3 | plano[29]<<2 | plano[30]<<1 | plano[31]<<0).astype(np.int32)
      return var1

# Main
def main():
      i = 0
      while True:
            i = i+1
            # Read from the sound card Chunk to CHUNK
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Pass from type bytes to int16 using the numpy library
            array_In = np.frombuffer(data, dtype=np.int16)
            # Calculate the transform and store it in six arrays
            # in floating point64
            coeffs = pywt.wavedec(array_In, 'db1', level=5)
            cA5, cD5, cD4, cD3, cD2, cD1 = coeffs
            # Pass each component to 32-bit planes
            cA5_planos = array_to_planos(cA5)
            cD5_planos = array_to_planos(cD5)
            cD4_planos = array_to_planes(cD4)
            cD3_planos = array_to_planos(cD3)
            cD2_planos = array_to_planos(cD2)
            cD1_planos = array_to_planos(cD1)

            if __debug__:
                  print("cA5 uno -->",cA5.dtype)
                  print("cD5 uno -->",len(cD5))
                  print("cD4 uno -->",len(cD4))
                  print("cD3 uno -->",len(cD3))
                  print("cD2 uno -->",len(cD2))
                  print("cD1 uno -->",len(cD1))
            # Pass each list of 32 planes to original component
            cA5_copy = planos_to_array(cA5_planos).astype(float)
            cD5_copy = planos_to_array(cD5_planos).astype(float)
            cD4_copy = planos_to_array(cD4_planos).astype(float)
            cD3_copy = planos_to_array(cD3_planos).astype(float)
            cD2_copy = planos_to_array(cD2_planos).astype(float)
            cD1_copy = planos_to_array(cD1_planos).astype(float)

            if __debug__:
                  print("cA5 dos --> ",cA5_copy)
                  print("cD5 dos --> ",len(cD5_copy))
                  print("cD4 dos --> ",len(cD4_copy))
                  print("cD3 dos --> ",len(cD3_copy))
                  print("cD2 dos --> ",len(cD2_copy))
                  print("cD1 dos --> ",cD5_copy.dtype)

            # Copy the individuals arrays in list coeffs1
            coeffs1 = [cA5_copy, cD5_copy, cD4_copy, cD3_copy, cD2_copy, cD1_copy]
            # Calculate the inverse transform and store as int16
            # with the numpy library
            array_Out = pywt.waverec(coeffs1, 'db1').astype(np.int16)
            # Transmit from the sound card the wavelet array casted
            # to bytes
            stream.write(array_Out.tobytes())


if __name__ == '__main__':
    main()
