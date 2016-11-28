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
    """
    realiza la TRANSFORMADA, normaliza y separa los datos en 
    las colecciones despues pega las colecciones en una sola
    """
    coeffs = wt.wavedec(frames, 'db1', level=2)
    #print(coeffs)
    transformada = []
    for i in coeffs:
        for e in i:
            transformada.append(int(round(e)))

    #print(transformada)
    #print(len(transformada))
    planos = {}
    for plano in range(0, 32):
        comp = 32-plano
        
        n = 0
        bloque = 0
        planos[plano] = []
        #print(planos)
        #print("caca", plano)
        for entero in transformada:
            #print(bin(entero & (2**comp)))
            temp = ((entero & (2**comp)) >> comp)
            #print(bin(temp))
            bloque += (temp << (32 - n)) # cada bloque tendra 32 bits
            #print(bin(bloque))
            n = n+1
            if n == 31:
                #print(plano)
                planos[plano].append(bloque)
                
                n = 0
                bloque = 0
    

    print(len(planos))
    for plane in planos:
        print("este es el plano nº ",plane)
        pepe = []
        posicion = 32-plane
        m = 0
        numero = 0
        for bloke in planos[plane]:
            pass
            #print(bin(bloke))

            #binario = ((bloke & (2**posicion)) >> posicion)
            #print(binario)
            #numero += (binario << (32 - m))
            #m = m+1
            #if m == 31:
             #   pepe.append(numero)
              #  m = 0
               # numero = 0
            #print(numero)



        #print("aqui termina un plano")

            #tempo = (y & (2**x) >> x)
            #print(tempo)




    #print(len(transformada))
    #print(planos)

    #aqui sacamos los planos de bits y devolvemos un
    #array de arrays de planos de bits

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
    data = stream.read(1024)
    #data = [5, 12, 3, 6]
    #data = [0, 0, 0, 0]
    frames = arraySecuencial(data)
    transform(frames)

if __name__ == '__main__':
    main()






