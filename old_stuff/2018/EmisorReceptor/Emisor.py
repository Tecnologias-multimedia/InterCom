#Emisor graba audio con UDP y PyAudio

#Libreria PyAudio
import pyaudio
# Libreria socket para poder mandar data con conexion udp
import socket
#Libreria threading para usar hilos
from threading import Thread

HOST = "localhost"
PORT = 12344

frames = []

#Enviamos audio usando udp
#Socket envia audio por puerto e ip indicado
def udpEnviar():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        if len(frames) > 0:
            udp.sendto(frames.pop(0), (HOST, PORT))
    udp.close()

#Grabacion de audio
def record(stream, CHUNK):    
    while True:
        frames.append(stream.read(CHUNK))

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

#Hilo que envia udp de lo que se graba
def main():
    CHUNK = tamanoChunk()
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100

    print("El tamaño del Chunk es de:",CHUNK)

    p = pyaudio.PyAudio()

    stream = p.open(format = FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    input = True,
                    frames_per_buffer = CHUNK,
                    )

    Tr = Thread(target = record, args = (stream, CHUNK,))
    Ts = Thread(target = udpEnviar)
    Tr.setDaemon(True)
    Ts.setDaemon(True)
    Tr.start()
    Ts.start()
    Tr.join()
    Ts.join()
    
if __name__ == "__main__":
    print("Emisor de Audio \n")
    main()
