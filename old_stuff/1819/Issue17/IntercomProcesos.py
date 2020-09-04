#Graba y recibe audio simultaneamente con UDP y PyAudio
#Usando dos hilos

#Libreria PyAudio
import pyaudio
# Libreria socket para poder mandar data con conexion udp
import socket
#Libreria multiprocessing para usar procesos
from multiprocessing import Process




CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
PORT = 12344

#Enviamos audio usando udp
#Socket envia audio por puerto e ip indicado
#Graba sonido y envia
def enviar(direccionIp, puerto):
    udpEnviar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    while True:
        data = stream.read(CHUNK)
        udpEnviar.sendto(data, (direccionIp, puerto))

#Recibimos audio usando udp
#Socket escucha por el puerto indicado
#Recibe datos y reproduce
def recibir(port_receiv):
    udpRecibir = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    direccion = ('0.0.0.0', port_receiv)
    udpRecibir.bind(direccion)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)

    while True:
        data, addr = udpRecibir.recvfrom(CHUNK*2)
        stream.write(data)

#Iniciamos dos procesos: un proceso para reproducir la entrada de socket 
#y otro proceso para enviar grabacion 
#Solicitamos direccion IP del host
def main():
    Tr = Process(target=recibir, args=(PORT,))
    Tr.daemon = True
    Tr.start()

    direccionHost = input("Host remitente: ")

    print("\nGrabando...")

    Te = Process(target=enviar, args=(direccionHost, PORT,))
    Te.daemon = True
    Te.start()
    Te.join()
    input()


if __name__ == '__main__':
    main()
