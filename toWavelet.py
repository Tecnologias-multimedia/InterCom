#cambiar los import de numpy y pywt a lo necesario
import numpy as np
import pywt as wt
from pyaudio import paInt16
from pyaudio import PyAudio

CHUNK = 1024
FORMAT = paInt16
CHANNELS = 1
RATE = 44100

def arraySecuencial(data):
    frames = []
    for i in range(0, 1024):
        frames.append(data[i])
    return frames


def main():
    return 0

if __name__ == '__main__':
    p = PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    data = stream.read(1024)
    arraySecuencial(data)
    main()
