#llamamos a las librerias necesarias para trabajar con puertos
#audio e hilos
import pyaudio
import socket
from threading import Thread

#variables que tendra el audio recibido para ser el optimo tiene que ser igual
#que el que nos envia el servidor
FORMAT = pyaudio.paInt16
CHUNK = 1024
CHANNELS = 2
RATE = 44100

frames = []

#Recibimos audio usando udp
#Socket escucha por el puerto indicado
def udpStream(CHUNK):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("localhost", 12345))
    
    while True:
        soundData, addr = udp.recvfrom(CHUNK * CHANNELS * 2)
        frames.append(soundData)
    udp.close()

#Reproduccion de audio
def reproducir(stream, CHUNK):
    BUFFER = 10
    while True:
            if len(frames) == BUFFER:
                while True:
                    stream.write(frames.pop(0), CHUNK)


#Hilo que reproduce lo que recibe udp
if __name__ == "__main__":

    print("Receptor de Audio \n")

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    output = True,
                    frames_per_buffer = CHUNK,
                    )
    #creamos los hilos necesarios y lo que ahcen para trabajar
    Ts = Thread(target = udpStream, args=(CHUNK,))
    Tp = Thread(target = reproducir, args=(stream, CHUNK,))
    Ts.setDaemon(True)
    Tp.setDaemon(True)
    Ts.start()
    Tp.start()
    Ts.join()
    Tp.join()