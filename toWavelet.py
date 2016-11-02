# -*- coding: utf-8 -*-
"""Modulo que hace la transformada y separa en planos el sonido raw

Modulo que recibe el sonido raw grabado en intercom
y lo convierte primero en un array de enteros,
despues le aplica la transformada y por ultimo
separa los datos ya transformados por planos de bits/bytes - corregir
Estos planos son enviados en los paquetes upd para su proxima reconstruccion

FALTA DECIDIR EL TIPO DE TRANSFORMADA A USAR.
"""

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
    """modulo de pruebas

    Aqui van los datos para realizar las pruebas sobre el modulo aislado
    """
    p = PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    data = stream.read(1024)
    frames = arraySecuencial(data)
    coeffs = wt.wavedec(frames, 'db1', level=5)
    cA5, cD5, cD4, cD3, cD2, cD1 = coeffs
    print(len(cD1))
    print(len(frames))

if __name__ == '__main__':
    main()
