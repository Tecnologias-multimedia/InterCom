#Emisor graba audio con UDP y PyAudio

#Libreria PyAudio
import pyaudio
# Libreria socket para poder mandar data con conexion udp
import socket
#Libreria threading para usar hilos
from threading import Thread

#variables que tendra el audio que enviamos
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

frames = []

#Enviamos audio usando udp
#Socket envia audio por puerto e ip indicado
def udpEnviar():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        if len(frames) > 0:
            udp.sendto(frames.pop(0), ("localhost", 12345))
    udp.close()

#Grabacion de audio
def record(stream, CHUNK):    
    while True:
        frames.append(stream.read(CHUNK))

#Hilos que envian udp de lo que se graba e unen el envio con la recepcion
if __name__ == "__main__":

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
