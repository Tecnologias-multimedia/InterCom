#
# SERVIDOR
#
import socket
import pyaudio

#UDP_IP="127.0.0.1"
UDP_IP = socket.gethostname()
UDP_PORT=5005

chunk = 1024
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
sock.bind( (UDP_IP,UDP_PORT) )

data, addr = sock.recvfrom( 3072 )
print ("received message:", data)



print ("* playing")
#for i in range(0, 44100 / chunk * RECORD_SECONDS):
#   print "get chunk %i" %i
while True:
   #data,addr = s.recvfrom(1024)
   data, addr = sock.recvfrom( 3072 )
   stream.write(data, chunk)
   #stream.write(data, chunk)
print ("* done")
