# -*- coding: utf-8 -*-
"""
    Modulo receptor transmisor de audio
    usamos upd para estas dos tareas con dos hilos simultaneos
"""

import threading
import socket
import sys

def receiver(port_receiv):
    """
        receptor de datos, usado como un hilo
        recibe el puerto por el que se desea escuchar
    """
    sock_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #cambiar a udp
    server_address = ('0.0.0.0', int(port_receiv)) # usar localhost para pruebas en el mismo portatil(?)
    sock_receiver.bind(server_address)

    #bucle para recibir audio
    while True:
        data, addr = sock_receiver.recvfrom(1024) # tamanhio de buffer no definitivo
        # recibir datos, descomprimirlos y etc. luego reproducir
        # reproducir -> print ("received message:", data)
    print(1)

def transmiter(ip_transm, port_transm):
    """
        transmisor de datos, usado como un segundo hilo
        recibe como parametros la ip del compañero al que enviar datos
        y el puerto por el que lo hace
    """
    sock_transmiter = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #cambiar a udp

    #bucle de transmision de datos
    while True:
        # grabar sonido comprimirlo y etc y enviarlo.
        sock.sendto(MESSAGE, (ip_transm, port_transm))
    print(2)


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
