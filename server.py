import socket
import pyaudio

#record
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 40

HOST = '127.0.0.1'    # The remote host
PORT = 5005              # The same port as used by the server

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("*recording")

frames = []

for i in range(0, int(RATE/CHUNK*RECORD_SECONDS)):
 data  = stream.read(CHUNK)
 frames.append(data)
 s.sendall(data)

print("*done recording")

stream.stop_stream()
stream.close()
p.terminate()
s.close()

print("*closed")
