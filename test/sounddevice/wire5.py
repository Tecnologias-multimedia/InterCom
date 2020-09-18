# The same as wire3.py, but using NumPy arrays.

import sounddevice as sd
import numpy as np

stream = sd.Stream(samplerate=44100, channels=2, dtype='int16')
stream.start()
while True:
    chunk, overflowed = stream.read(stream.read_available)
    if overflowed:
        print("Overflow")
    stream.write(chunk)
