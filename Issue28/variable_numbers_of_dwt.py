# PyAudio to capture and broadcast audio
import pyaudio
# NumPy to change variable types
import numpy as np
# Pywt to calculate Discrete Wavelet Transform (DWT)
import pywt
# SciPy to calculate entropy
import scipy.stats as st
# Argparse to receive arguments for command line
import argparse
# Math to calculate log in base 2
import math

# Declaration of variables
FORMAT = pyaudio.paInt16
p = pyaudio.PyAudio()

# Function that a component passes in 32-bit planes assigned to a list
def array_to_planos(planos):
    subbanda = []
    for i in range(0, len(planos)):
        b = planos[i].astype(np.int32)
        c = [(b & (0b1<<31)) >> 31,(b & (0b1<<30)) >> 30, (b & (0b1<<29)) >> 29, (b & (0b1<<28)) >> 28
                , (b & (0b1<<27)) >> 27, (b & (0b1<<26)) >> 26, (b & (0b1<<25)) >> 25, (b & (0b1<<24)) >> 24
                , (b & (0b1<<23)) >> 23, (b & (0b1<<22)) >> 22, (b & (0b1<<21)) >> 21, (b & (0b1<<20)) >> 20
                , (b & (0b1<<19)) >> 19, (b & (0b1<<18)) >> 18, (b & (0b1<<17)) >> 17, (b & (0b1<<16)) >> 16
                , (b & (0b1<<15)) >> 15, (b & (0b1<<14)) >> 14, (b & (0b1<<13)) >> 13, (b & (0b1<<12)) >> 12
                , (b & (0b1<<11)) >> 11, (b & (0b1<<10)) >> 10, (b & (0b1<<9)) >> 9, (b & (0b1<<8)) >> 8
                , (b & (0b1<<7)) >> 7, (b & (0b1<<6)) >> 6, (b & (0b1<<5)) >> 5, (b & (0b1<<4)) >> 4
                , (b & (0b1<<3)) >> 3, (b & (0b1<<2)) >> 2, (b & (0b1<<1)) >> 1, (b & (0b1<<0)) >> 0]
        subbanda.append(c)
    return subbanda


# Function that passes the list of 32 bits to decimal array
def planos_to_array(planos):
    subbanda = []
    for i in range(0, len(planos)):
        plano = planos[i]
        var1 = (plano[0]<<31 | plano[1]<<30 | plano[2]<<29 | plano[3]<<28 | plano[4]<<27 | plano[5]<<26 | plano[6]<<25 | 
                plano[7]<<24 | plano[8]<<23 | plano[9]<<22 | plano[10]<<21 | plano[11]<<20 | plano[12]<<19 | plano[13]<<18 | 
                plano[14]<<17 | plano[15]<<16 | plano[16]<<15 | plano[17]<<14 | plano[18]<<13 | plano[19]<<12 | plano[20]<<11 | 
                plano[21]<<10 | plano[22]<<9 | plano[23]<<8 | plano[24]<<7 | plano[25]<<6 | plano[26]<<5 | plano[27]<<4 | 
                plano[28]<<3 | plano[29]<<2 | plano[30]<<1 | plano[31]<<0).astype(np.int32).astype(float)
        subbanda.append(var1)
    return subbanda

# Main
def main():
    # Receive parameters for command line, if not, they have default parameters 
    parser = argparse.ArgumentParser(description = 'Arguments')
    parser.add_argument('-c', '--chunk', help='chunk size', type=int, default=1024)
    parser.add_argument('-r', '--rate', help='sampling rate', type=int, default=44100)
    parser.add_argument('-nc', '--nchannels', help='number of channels', type=int, default=1)
    parser.add_argument('-l', '--levels', help='numbers of levels dwt', type=int, default=5)
    args = parser.parse_args()
    # Check if the level of dwt stay in range
    if (args.chunk < 2**args.levels):
        print('Numbers of levels dwt is not valid. The max levels dwt for chunk size', args.chunk, 'is', int(math.log(args.chunk,2)))
        quit()

    # Print input parameters 
    if __debug__:
        print('Input parameters:')
        print('\tChunk size:',args.chunk)
        print('\tSampling rate:',args.rate)
        print('\tNumbers of channels:',args.nchannels)
        print('\tNumbers of levels of dwt:',args.levels)

    # Variable that we use to capture and broadcast audio
    stream = p.open(format=FORMAT,
            channels=args.nchannels,
            rate=args.rate,
            input=True,
            output=True,
            frames_per_buffer=args.chunk)

    i = 0
    while True:
        i = i+1
        # Read from the sound card Chunk to CHUNK
        data = stream.read(args.chunk, exception_on_overflow=False)
        # Pass from type bytes to int16 using the numpy library
        array_In = np.frombuffer(data, dtype=np.int16)
        # Calculate the transform and store it in arrays in floats
        coeffs = pywt.wavedec(array_In, 'db1', level=args.levels)
        # Pass each component to 32-bit planes
        coeffs_planos = array_to_planos(coeffs)
        # Pass each list of list in 32 planes to original coeffs
        coeffs1 = planos_to_array(coeffs_planos)
        # Calculate the inverse transform and store as int16
        # with the numpy library
        array_Out = pywt.waverec(coeffs1, 'db1').astype(np.int16)
        # Transmit to the sound card the wavelet array casted
        # to bytes
        stream.write(array_Out.tobytes())


if __name__ == '__main__':
    main()
