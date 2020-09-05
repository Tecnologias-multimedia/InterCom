# Introducing CPU load in the pipeline. Result, latency and lost of chunks.

import sounddevice as sd
import numpy as np

CHUNK_SIZE = 1024

stream = sd.Stream(samplerate=44100, channels=2, dtype='int16')
stream.start()
while True:
    chunk, overflowed = stream.read(CHUNK_SIZE)
    if overflowed:
        print("Overflow")
    x = 0
    for i in range(1000000):
        x += 1
    stream.write(chunk)
