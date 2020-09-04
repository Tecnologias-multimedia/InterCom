# Librerias necesarias para recibir audio por udp
import socket
import pyaudio

# Variables del audio (se recomienda que sean las mismas que las del servidor)
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

# Conectamos al que nos envia los datos
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 50007))

# Crear variable de pyaudio
p = pyaudio.PyAudio()
# Creamos otra variable para trabajar con pyaudio
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)
# Iniciamos el audio
stream.start_stream()


def main():
    print("*_>recording")
# Se va leyendo el audio miemtras se recibe
    while True:
        try:
            data = stream.read(CHUNK)
        except Exception as e:
            data = '\x00' * CHUNK
        s.sendall(data)

    print("*_>done recording")

# Cerramos el audio terminamos con la libreria pyaudio
# Y cerramos el trabajo con el puerto
    stream.stop_stream()
    stream.close()
    p.terminate()
    s.close()


if __name__ == '__main__':
    main()