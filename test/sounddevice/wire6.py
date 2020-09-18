# Introducing CPU load in the pipeline. Result, latency and lost of chunks.

import sounddevice as sd
import numpy as np

stream = sd.Stream(samplerate=44100, channels=2, dtype='int16')
stream.start()
while True:
    chunk, overflowed = stream.read(stream.read_available)
    if overflowed:
        print("Overflow")
    x = 0
    for i in range(1000000):
        x += 1
    stream.write(chunk)
