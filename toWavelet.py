# -*- coding: utf-8 -*-
"""Modulo que hace la transformada y separa en planos el sonido raw

Modulo que recibe el sonido raw grabado en intercom
y lo convierte primero en un array de enteros,
despues le aplica la transformada (esta ha de ser normalizada a enteros) y por ultimo
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
VALORES = 32

def arraySecuencial(data):
    frames = []
    for i in range(0, len(data)):
        frames.append(data[i])
    return frames

def transform(frames):
    """realiza la TRANSFORMADA, normaliza y separa los datos en las colecciones

    despues pega las colecciones en una sola"""
    coeffs = wt.wavedec(frames, 'db1', level=2)
    transformada = []
    for i in coeffs:
        for e in i:
            transformada.append(int(round(e)))

    planos = {}
    for plano in range(0, 32):
        comp = 32-plano
        n = 0
        bloque = 0
        planos[plano] = []

        for v in transformada:
            temp = ((v & (2**comp)) >> comp)
            bloque += (temp << (32 - n))
            n = n+1
            if n == 31:
                planos[plano].append(bloque)
                n = 0
                bloque = 0
    
    print(transformada)
    print(planos)

    #aqui sacamos los planos de bits y devolvemos un
    #array de arrays de planos de bits

def main():
    """modulo de pruebas

    Aqui van los datos para realizar las pruebas sobre el modulo aislado
    Tambien sirve como ejemplo de uso
    """
    p = PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    data = stream.read(1024)
    #data = [5, 12, 3, 6]
    frames = arraySecuencial(data)
    transform(frames)

if __name__ == '__main__':
    main()