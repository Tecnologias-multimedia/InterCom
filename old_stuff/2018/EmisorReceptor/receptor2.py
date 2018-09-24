import socket

import pyaudio

CHUNK = 8192
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5

HOST = 'localhost'    # The remote host
PORT = 50007             # The same port as used by the server

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

stream.start_stream()


def main():
    print("*_>recording")

    while True:
        try:
            data = stream.read(CHUNK)
        except Exception as e:
           
            data = '\x00' * CHUNK

        
        s.sendall(data)

    print("*_>done recording")

    stream.stop_stream()
    stream.close()
    p.terminate()
    s.close()

    print("*_>closed")

if __name__ == '__main__':
    main()