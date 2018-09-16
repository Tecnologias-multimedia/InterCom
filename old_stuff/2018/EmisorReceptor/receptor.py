#Receptor reproduce audio con UDP y PyAudio

#Libreria PyAudio
import pyaudio
#Libreria Libreria socket para poder recibir data con conexion udp
import socket
#Libreria threading para usar hilos
from threading import Thread

HOST = "localhost"
PORT = 12344

frames = []

#Recibimos audio usando udp
#Socket escucha por el puerto indicado
def udpRecibir(CHUNK):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((HOST, PORT))
    
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

#Tamaño del Chunk solicitado mediante teclado
#Excepcion String a int si hay valor de error
#Si el tamaño es introducido mal será de 1024
def tamanoChunk():
    try:
        print("Indica el tamaño de Chunk (Recomiendo 1024)")
        ChunkSize = int(input())
    except ValueError:
        print("Has introducido mal el tamaño. \nUtilizando tamaño 1024")
        ChunkSize = 1024
    return ChunkSize

#Hulo que reproduce lo que recibe udp
if __name__ == "__main__":

    print("Receptor de Audio \n")
    
    FORMAT = pyaudio.paInt16
    CHUNK = tamanoChunk()
    CHANNELS = 2
    RATE = 44100

    print("El tamaño del Chunk es de:",CHUNK)

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    output = True,
                    frames_per_buffer = CHUNK,
                    )
    
    Ts = Thread(target = udpRecibir, args=(CHUNK,))
    Tp = Thread(target = reproducir, args=(stream, CHUNK,))
    Ts.setDaemon(True)
    Tp.setDaemon(True)
    Ts.start()
    Tp.start()
    Ts.join()
    Tp.join()
