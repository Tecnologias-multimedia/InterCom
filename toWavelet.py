# -*- coding: utf-8 -*-
"""Modulo que hace la transformada y separa en planos el sonido raw

Modulo que recibe el sonido raw grabado en intercom
y lo convierte primero en un array de enteros,
despues le aplica la transformada (esta ha de ser normalizada a enteros) y por
último separa los datos ya transformados por planos de bits/bytes - corregir
Estos planos son enviados en los paquetes upd para su proxima reconstruccion

FALTA DECIDIR EL TIPO DE TRANSFORMADA A USAR.
"""

# Cambiar los import de numpy y pywt a lo necesario
# import numpy as np
import pywt as wt
from ctypes import c_int32
from pyaudio import paInt16
from pyaudio import PyAudio

CHUNK = 1024
FORMAT = paInt16
CHANNELS = 1
RATE = 44100
VALORES = 32
ITERACIONESDWT = 9


def arraySecuencial(data):
    frames = []
    for i in range(0, len(data)):
        frames.append(data[i])
    # print(frames)
    return frames


def transform(frames):
    """
    realiza la TRANSFORMADA, normaliza y separa los datos en
    las colecciones despues pega las colecciones en una sola
    """
    coeffs = wt.wavedec(frames, 'db1', level=ITERACIONESDWT)
    transformada = []
    for i in coeffs:
        for e in i:
            transformada.append(int(round(e)))

    planos = {}
    for plano in range(0, 32):
        comp = 31-plano

        n = 0
        bloque = 0
        planos[plano] = []

        for entero in transformada:
            if plano == 0:
                temp = ((entero & (2**comp)) >> comp)
            else:
                temp = ((abs(entero) & (2**comp)) >> comp)
            bloque += (temp << (31 - n))  # Cada bloque tendra 32 bits
            n = n+1
            if n == 32:
                planos[plano].append(bloque)
                n = 0
                bloque = 0
    return planos


def detransform(diciPlanos):
    destransformacion = []
    for plano in diciPlanos:
        n = 31-plano
        if plano == 0:
            for bloque in diciPlanos[plano]:
                for bit in reversed(range(0, 32)):
                    temp = ((bloque & (2**bit)) >> bit)
                    if temp == 1:
                        # Un truco para almacenar el signo ya que es
                        # imposible almacenar -0
                        temp = c_int32(-1)
                    else:
                        temp = c_int32(temp << n)

                    destransformacion.append(temp.value)
        else:
            cuentaBloque = 0
            for bloque in diciPlanos[plano]:
                for bit in reversed(range(0, 32)):
                    temp = ((bloque & (2**bit)) >> bit)
                    temp = temp << n
                    if destransformacion[cuentaBloque] >= 0:
                        destransformacion[cuentaBloque] += temp
                    else:
                        destransformacion[cuentaBloque] -= temp
                    cuentaBloque += 1
    # Resto 1 por que hemos almacenado -1 para los negativos
    destransformacion = list(map(sumaUnoNegativos, destransformacion))

    coeffs = []
    stack = 0
    w = wt.Wavelet('db1')
    values = wt.dwt_max_level(len(destransformacion), w) - ITERACIONESDWT
    for x in range(0, ITERACIONESDWT+1):
        trick = ((2 ** (values)) * (2 ** x))
        coeffs.append(destransformacion[stack:trick])
        stack = trick
    destransformacion = wt.waverec(coeffs, 'db1')
    print(list(map(len, coeffs)))
    destransformacion = destransformacion.tolist()
    destransformacion = list(map(round, destransformacion))

    return destransformacion


def sumaUnoNegativos(x):
    if x < 0:
        return x+1
    return x

    # Aqui sacamos los planos de bits y devolvemos un
    # Array de arrays de planos de bits


def main():
    """modulo de pruebas

    Aqui van los datos para realizar las pruebas sobre el
    modulo aislado Tambien sirve como ejemplo de uso
    """
    p = PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    data = stream.read(512)
    frames = arraySecuencial(data)
    diciPlanos = transform(frames)
    # dest = detransform(diciPlanos)
    detransform(diciPlanos)


if __name__ == '__main__':
    main()
