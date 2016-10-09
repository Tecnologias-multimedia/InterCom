import socket
import pyaudio

#Stream Data
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
frames = []

#Host and Port
HOST = '127.0.0.1'
PORT = 5005

#Initializing pyaudio and buffer.
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK)

#Creating Socket and wait for a client.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
conn, addr = s.accept()
print ('Connected by', addr)
data = conn.recv(CHUNK * CHANNELS * 2)

for i in range(0, int(RATE/CHUNK*5)):
    stream.write(data)
    data = conn.recv(CHUNK * CHANNELS * 2)
    frames.append(data)
    print (i)

stream.stop_stream()
stream.close()
p.terminate()
conn.close()
