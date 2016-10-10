# -*- coding: utf-8 -*-
"""
    Modulo receptor emisor de audio
    usamos upd para estas dos tareas con dos hilos simultaneos
"""

import threading
import socket
import pyaudio
#import sys

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
frames = []

def receiver(port_receiv):
    

    """
        receptor de datos, usado como un hilo
        recibe el puerto por el que se desea escuchar
    """
    sock_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #cambiar a udp
    server_address = ('0.0.0.0', int(port_receiv)) # usar localhost para pruebas en el mismo portatil(?)
    sock_receiver.bind(server_address)

    print(1)
    #bucle para recibir audio

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)
    while True:
        data, addr = sock_receiver.recvfrom(2048) # tamanhio de buffer no definitivo
        stream.write(data)
        # recibir datos, descomprimirlos y etc. luego reproducir
        # print ("received message:", data.decode('utf-8'))

def transmiter(ip_transm, port_transm):
    
    """
        emisor de datos, usado como un segundo hilo
        recibe como parametros la ip del compañero al que enviar datos
        y el puerto por el que lo hace
    """
    sock_transmiter = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #cambiar a udp

    print(2)
    #bucle de transmision de datos

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    while True:
        data = stream.read(1024)
        #MESSAGE = "El arcipreste de Hita fuma petardos de marihuana."
        # grabar sonido comprimirlo y etc y enviarlo.
        #sock_transmiter.sendto(data, (ip_transm, int(port_transm)))
        sock_transmiter.sendto(data, (ip_transm, int(port_transm)))
if __name__ == '__main__':
    #establecemos puerto de escucha
    port_receiv = input("Introduce el puerto para recibir: ")

    # iniciamos el hilo reporoductor que lee lo que entra de udp
    r = threading.Thread(target=receiver, args=(port_receiv))
    r.daemon = True
    r.start()

    # solicitamos los datos del "peer"
    host_transm = input("Introduce la ip del host: ")
    port_transm = input("Introduce el puerto del host: ")

    # hilo para enviar udp de lo que se graba
    t = threading.Thread(target=transmiter, args=(host_transm, port_transm))
    t.daemon = True
    t.start()

esperandoEntradaDatos = input("Introduce algo mas: ")