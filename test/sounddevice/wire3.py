# Basic wire using blocking I/O. Python buffers are used.

import sounddevice as sd

CHUNK_SIZE = 1024

stream = sd.RawStream(samplerate=44100, channels=2, dtype='int16')
stream.start()
while True:
    chunk, overflowed = stream.read(CHUNK_SIZE)
    if overflowed:
        print("Overflow")
    stream.write(chunk)
