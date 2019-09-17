"""
PyAudio Example: Make a wire between input and output (i.e., record a
few samples and play them back immediately).
"""

import pyaudio
import sys

CHUNK = 256
WIDTH = 2
CHANNELS = 2
RATE = 44100

p = pyaudio.PyAudio()

input = p.open(format=p.get_format_from_width(WIDTH),
               channels=CHANNELS,
               rate=RATE,
               input=True,
               frames_per_buffer=CHUNK)

output = p.open(format=p.get_format_from_width(WIDTH),
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK)

print("* recording")

while True:
    data = input.read(CHUNK)
    sys.stderr.write(" {}".format(data[0])); sys.stderr.flush()
    output.write(data, CHUNK)

print("* done")

input.stop_stream()
input.close()

output.stop_stream()
output.close()

p.terminate()
