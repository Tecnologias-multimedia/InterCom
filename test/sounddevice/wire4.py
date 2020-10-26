# Basic ADC/DAC-wiring using non-blocking I/O. Python buffers are used.

import sounddevice as sd

stream = sd.RawStream(samplerate=44100, channels=2, dtype='int16')
stream.start()

while True:
    chunk, overflowed = stream.read(stream.read_available)
    #print(len(chunk), end=' ', flush=True)
    if overflowed:
        print("Overflow")
    stream.write(chunk)
