# Basic SDC/DAC-wiring using blocking I/O. Python buffers are used.

import sounddevice as sd

stream = sd.RawStream(samplerate=44100, channels=2, dtype='int16')
stream.start()

CHUNK_SIZE = 32
while True:
    chunk, overflowed = stream.read(CHUNK_SIZE)
    if overflowed:
        print("Overflow")
    stream.write(chunk)
