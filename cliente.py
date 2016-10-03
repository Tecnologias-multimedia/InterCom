#
#    CLIENTE
#
import socket
import pyaudio


#UDP_IP="127.0.0.1"
UDP_IP= socket.gethostname()

UDP_PORT=5005
MESSAGE=("Hello, World!")

print ("UDP target IP:", UDP_IP)
print ("UDP target port:", UDP_PORT)
print ("message:", MESSAGE)


chunk = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                output = True,
                frames_per_buffer = chunk)

sock = socket.socket( socket.AF_INET,
                      socket.SOCK_DGRAM ) # UDP
sock.sendto( '', (UDP_IP, UDP_PORT) )

print ("* recording")
#for i in range(0, 44100 / chunk * RECORD_SECONDS):
while True:
    MESSAGE = stream.read(chunk)
    sock = socket.socket( socket.AF_INET,socket.SOCK_DGRAM )#internet # UDP
    sock.sendto( '', (UDP_IP, UDP_PORT) )
    sock.sendto( '', (UDP_IP, UDP_PORT) )
    sock.sendto( '', (UDP_IP, UDP_PORT) )


print ("* done")
