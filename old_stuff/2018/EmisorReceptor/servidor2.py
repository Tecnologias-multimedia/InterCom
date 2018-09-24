import Queue
import socket
import wave

import pyaudio

CHUNK = 8192
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100


HOST = 'localhost'     # Symbolic name meaning all available interfaces
PORT = 50007              # Arbitrary non-privileged port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
conn, addr = s.accept()
print 'Connected by', addr

p = pyaudio.PyAudio()
stream = p.open(format=p.get_format_from_width(2),
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK)
q = Queue.Queue()

frames = []

stream.start_stream()


def main():
    data = conn.recv(CHUNK)

    while data != '':
        q.put(data)
        if not q.empty():
            stream.write(q.get())

        # stream.write(data)
        data = conn.recv(CHUNK)
        frames.append(data)

    

    stream.stop_stream()
    stream.close()
    p.terminate()
    conn.close()

if __name__ == '__main__':
    main()