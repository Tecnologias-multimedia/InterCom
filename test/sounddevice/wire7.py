# Moving the computation to a process: result, a core loadad, but the
# other process working without any special issue.

import multiprocessing
import sounddevice as sd
import numpy as np

def computation():
    while True:
        x = 0
        for i in range(1000000):
            x += 1

p = multiprocessing.Process(target=computation)
p.start()

stream = sd.Stream(samplerate=44100, channels=2, dtype='int16')
stream.start()
while True:
    chunk, overflowed = stream.read(stream.read_available)
    if overflowed:
        print("Overflow")
    stream.write(chunk)
