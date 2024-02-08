# https://www.henryschmale.org/2021/01/07/pygame-linein-audio-viz.html

import pyaudio
import numpy as np
from math import sqrt
import time
import pygame

pygame.init()

RATE = 44100
CHUNK = int((1/30) * RATE)
FORMAT = pyaudio.paInt16

print (CHUNK)

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
    channels=1,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK)

print("*recording")

SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((CHUNK, SCREEN_HEIGHT))

done = False
while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
            break
    start = time.time()
    buff = stream.read(CHUNK)
    data = np.frombuffer(buff, dtype=np.int16)
    fft_complex = np.fft.fft(data, n=CHUNK)
    #fft_distance = np.zeros(len(fft_complex))

    screen.fill((0,0,0))
    color = (0,128,1)
    s = 0
    max_val = sqrt(max(v.real * v.real + v.imag * v.imag for v in fft_complex))
    scale_value = SCREEN_HEIGHT / max_val
    for i,v in enumerate(fft_complex):
        #v = complex(v.real / dist1, v.imag / dist1)
        dist = sqrt(v.real * v.real + v.imag * v.imag)
        mapped_dist = dist * scale_value
        s += mapped_dist
    
        pygame.draw.line(screen, color, (i, SCREEN_HEIGHT), (i, SCREEN_HEIGHT - mapped_dist))
    print(s/len(fft_complex))


    pygame.display.flip()

    end = time.time()

    # print(end - start)

    
