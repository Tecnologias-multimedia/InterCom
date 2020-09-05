# The same as wire3.py, but using NumPy arrays.

import sounddevice as sd
import numpy as np

CHUNK_SIZE = 1024

stream = sd.Stream(samplerate=44100, channels=2, dtype='int16')
stream.start()
while True:
    chunk, overflowed = stream.read(CHUNK_SIZE)
    if overflowed:
        print("Overflow")
    stream.write(chunk)
