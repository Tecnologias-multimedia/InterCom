# PyAudio to capture and broadcast audio
import pyaudio
# NumPy to change variable types
import numpy as np
# Pywt to calculate Discrete Wavelet Transform (DWT)
import pywt
# SciPy to calculate entropy
import scipy.stats as st
# Argparse to receive arguments for command line
import argparse
# Math to calculate log in base 2
import math
# Threading to use thread
from threading import Thread
# Socket to send data using udp
import socket

# Declaration of variables
FORMAT = pyaudio.paInt16
p = pyaudio.PyAudio()

# Function that take all component and passes in 32-bit planes assigned to a list
def array_to_planos(components):
    a_components = np.concatenate(components, axis=0)   # Example: 6 components (6 individual array) in a single array
    b = a_components.astype(np.int32)
    list_32planes = [(b & (0b1<<31)) >> 31,(b & (0b1<<30)) >> 30, (b & (0b1<<29)) >> 29, (b & (0b1<<28)) >> 28
            , (b & (0b1<<27)) >> 27, (b & (0b1<<26)) >> 26, (b & (0b1<<25)) >> 25, (b & (0b1<<24)) >> 24
            , (b & (0b1<<23)) >> 23, (b & (0b1<<22)) >> 22, (b & (0b1<<21)) >> 21, (b & (0b1<<20)) >> 20
            , (b & (0b1<<19)) >> 19, (b & (0b1<<18)) >> 18, (b & (0b1<<17)) >> 17, (b & (0b1<<16)) >> 16
            , (b & (0b1<<15)) >> 15, (b & (0b1<<14)) >> 14, (b & (0b1<<13)) >> 13, (b & (0b1<<12)) >> 12
            , (b & (0b1<<11)) >> 11, (b & (0b1<<10)) >> 10, (b & (0b1<<9)) >> 9, (b & (0b1<<8)) >> 8
            , (b & (0b1<<7)) >> 7, (b & (0b1<<6)) >> 6, (b & (0b1<<5)) >> 5, (b & (0b1<<4)) >> 4
            , (b & (0b1<<3)) >> 3, (b & (0b1<<2)) >> 2, (b & (0b1<<1)) >> 1, (b & (0b1<<0)) >> 0]
    return list_32planes

# Function that passes the list of 32 bits to decimal array
def planos_to_array(plano, levels):
    var1 = (plano[31]<<31 | plano[30]<<30 | plano[29]<<29 | plano[28]<<28 | plano[27]<<27 | plano[26]<<26 | plano[25]<<25 | 
            plano[24]<<24 | plano[23]<<23 | plano[22]<<22 | plano[21]<<21 | plano[20]<<20 | plano[19]<<19 | plano[18]<<18 | 
            plano[17]<<17 | plano[16]<<16 | plano[15]<<15 | plano[14]<<14 | plano[13]<<13 | plano[12]<<12 | plano[11]<<11 | 
            plano[10]<<10 | plano[9]<<9 | plano[8]<<8 | plano[7]<<7 | plano[6]<<6 | plano[5]<<5 | plano[4]<<4 | 
            plano[3]<<3 | plano[2]<<2 | plano[1]<<1 | plano[0]<<0).astype(np.int32).astype(float)
    subbands = []
    buffer = []
    jumps = [0]*(levels+1)
    for z in range(0, levels+1):
        jumps[z] = 2**(int(math.log(len(var1),2))-(levels-z))-1
    count = 0
    for x in range(0, len(var1)):
        buffer.append(var1[x])
        if (x == jumps[count]):
            subbands.append(np.array(buffer))
            buffer = []
            count += 1
    return subbands

#Enviamos audio usando udp
#Socket envia audio por puerto e ip indicado
#Graba sonido y envia
def enviar(direccionIp, port, channels, rate, chunk_size, levels):
    udpEnviar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk_size)

    while True:
        # Read from the sound card Chunk to CHUNK
        data = stream.read(chunk_size, exception_on_overflow=False)
        # Pass from type bytes to int16 using the numpy library
        array_In = np.frombuffer(data, dtype=np.int16)
        # Calculate the transform and store it in arrays in floats
        coeffs = pywt.wavedec(array_In, 'db1', level=levels)
        # Pass each component to 32-bit planes
        coeffs_planos = array_to_planos(coeffs)
        # Send 32-bit planes
        for i in range(0,32):
            a = np.insert(coeffs_planos[i].astype(np.int8),0,(31-i)) 
            udpEnviar.sendto(a.tobytes(), (direccionIp, port))
            

#Recibimos audio usando udp
#Socket escucha por el puerto indicado
#Recibe datos y reproduce
def recibir(port, channels, rate, chunk_size, levels):
    udpRecibir = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    direccion = ('0.0.0.0', port)
    udpRecibir.bind(direccion)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=channels,
                    rate=rate,
                    output=True,
                    frames_per_buffer=chunk_size)
    # Create buffer 
    buffer_planes = [0]*32
    while True:
        # receive 32 packages
        for i in range(0,32):
            plane, addr = udpRecibir.recvfrom(1025)
            plane = np.frombuffer(plane, dtype=np.int8)
            # Example: plane [32,0,0,0,0, ... ,1,0,1]
            index = plane[0]
            buffer_planes[index]=(plane[1:]).astype(np.int32)
        # Pass each list of list in 32 planes to original subbands
        subbands = planos_to_array(buffer_planes, levels)
        # Calculate the inverse transform and store as int16
        # with the numpy library
        a_Out = pywt.waverec(subbands, 'db1').astype(np.int16)
        # Transmit to the sound card the wavelet array casted
        # to bytes
        stream.write(a_Out.tobytes())

#Iniciamos dos hilos: un hilo para reproducir la entrada de socket 
#y otro hilo para enviar grabacion 
#Solicitamos direccion IP del host
def main():
    # Receive parameters for command line, if not, they have default parameters 
    parser = argparse.ArgumentParser(description = 'Arguments')
    parser.add_argument('-c', '--chunk_size', help='chunk size', type=int, default=1024)
    parser.add_argument('-r', '--rate', help='sampling rate', type=int, default=44100)
    parser.add_argument('-nc', '--nchannels', help='number of channels', type=int, default=1)
    parser.add_argument('-l', '--levels', help='numbers of levels dwt', type=int, default=5)
    parser.add_argument('-p', '--port', help='port', type=int, default=443)
    args = parser.parse_args()
    # Check if the level of dwt stay in range
    if (args.chunk_size < 2**args.levels):
        print('Numbers of levels dwt is not valid. The max levels dwt for chunk size', args.chunk, 'is', int(math.log(args.chunk,2)))
        quit()

    # Print input parameters 
    if __debug__:
        print('Input parameters:')
        print('\tChunk size:',args.chunk_size)
        print('\tSampling rate:',args.rate)
        print('\tNumbers of channels:',args.nchannels)
        print('\tNumbers of levels of dwt:',args.levels)

    Tr = Thread(target=recibir, args=(args.port, args.nchannels, args.rate, args.chunk_size, args.levels,))
    Tr.daemon = True
    Tr.start()

    direccionHost = input("Host remitente: ")

    print("\nGrabando...")

    Te = Thread(target=enviar, args=(direccionHost, args.port, args.nchannels, args.rate, args.chunk_size, args.levels,))
    Te.daemon = True
    Te.start()
    Te.join()
    input()


if __name__ == '__main__':
    main()
