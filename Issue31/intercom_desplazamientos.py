import pyaudio                      # http://people.csail.mit.edu/hubert/pyaudio/
import numpy as np                  # https://www.numpy.org
import pywt                         # https://pywavelets.readthedocs.io
#import scipy.stats as st            # https://www.scipy.org/
import argparse                     # https://docs.python.org/3/library/argparse.html
import math                         # https://docs.python.org/3/library/math.html
import multiprocessing              # https://docs.python.org/3/library/multiprocessing.html
import socket                       # https://docs.python.org/3/library/socket.html
import time                         # https://docs.python.org/3/library/time.html

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

def encode(plane):
    # Recive plano a plano (del 31 al 0)
    length = int(len(plane)/64)
    buffer = np.zeros((length,), dtype = np.uint64)
    inicio = 0
    fin = 0
    for i in range(0, length):
        fin += 64
        buffer[i] = (plane[0+inicio]<<63 | plane[1+inicio]<<62 | plane[2+inicio]<<61 | plane[3+inicio]<<60
            | plane[4+inicio]<<59 | plane[5+inicio]<<58 | plane[6+inicio]<<57 | plane[7+inicio]<<56
            | plane[8+inicio]<<55 | plane[9+inicio]<<54 | plane[10+inicio]<<53 | plane[11+inicio]<<52
            | plane[12+inicio]<<51 | plane[13+inicio]<<50 | plane[14+inicio]<<49 | plane[15+inicio]<<48
            | plane[16+inicio]<<47 | plane[17+inicio]<<46 | plane[18+inicio]<<45 | plane[19+inicio]<<44
            | plane[20+inicio]<<43 | plane[21+inicio]<<42 | plane[22+inicio]<<41 | plane[23+inicio]<<40
            | plane[24+inicio]<<39 | plane[25+inicio]<<38 | plane[26+inicio]<<37 | plane[27+inicio]<<36
            | plane[28+inicio]<<35 | plane[29+inicio]<<34 | plane[30+inicio]<<33 | plane[31+inicio]<<32
            | plane[32+inicio]<<31 | plane[33+inicio]<<30 | plane[34+inicio]<<29 | plane[35+inicio]<<28
            | plane[36+inicio]<<27 | plane[37+inicio]<<26 | plane[38+inicio]<<25 | plane[39+inicio]<<24
            | plane[40+inicio]<<23 | plane[41+inicio]<<22 | plane[42+inicio]<<21 | plane[43+inicio]<<20
            | plane[44+inicio]<<19 | plane[45+inicio]<<18 | plane[46+inicio]<<17 | plane[47+inicio]<<16
            | plane[48+inicio]<<15 | plane[49+inicio]<<14 | plane[50+inicio]<<13 | plane[51+inicio]<<12
            | plane[52+inicio]<<11 | plane[53+inicio]<<10 | plane[54+inicio]<<9 | plane[55+inicio]<<8
            | plane[56+inicio]<<7 | plane[57+inicio]<<6 | plane[58+inicio]<<5 | plane[59+inicio]<<4
            | plane[60+inicio]<<3 | plane[61+inicio]<<2 | plane[62+inicio]<<1 | plane[63+inicio]<<0).astype(np.uint64)
        inicio = fin
    return buffer


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

def decode(plane):
    a = [(plane & np.uint64(0b1<<63)) >> 63,(plane & np.uint64(0b1<<62)) >> 62, (plane & np.uint64(0b1<<61)) >> 61, (plane & np.uint64(0b1<<60)) >> 60
        , (plane & np.uint64(0b1<<59)) >> 59, (plane & np.uint64(0b1<<58)) >> 58, (plane & np.uint64(0b1<<57)) >> 57, (plane & np.uint64(0b1<<56)) >> 56
        , (plane & np.uint64(0b1<<55)) >> 55, (plane & np.uint64(0b1<<54)) >> 54, (plane & np.uint64(0b1<<53)) >> 53, (plane & np.uint64(0b1<<52)) >> 52
        , (plane & np.uint64(0b1<<51)) >> 51, (plane & np.uint64(0b1<<50)) >> 50, (plane & np.uint64(0b1<<49)) >> 49, (plane & np.uint64(0b1<<48)) >> 48
        , (plane & np.uint64(0b1<<47)) >> 47, (plane & np.uint64(0b1<<46)) >> 46, (plane & np.uint64(0b1<<45)) >> 45, (plane & np.uint64(0b1<<44)) >> 44
        , (plane & np.uint64(0b1<<43)) >> 43, (plane & np.uint64(0b1<<42)) >> 42, (plane & np.uint64(0b1<<41)) >> 41, (plane & np.uint64(0b1<<40)) >> 40
        , (plane & np.uint64(0b1<<39)) >> 39, (plane & np.uint64(0b1<<38)) >> 38, (plane & np.uint64(0b1<<37)) >> 37, (plane & np.uint64(0b1<<36)) >> 36
        , (plane & np.uint64(0b1<<35)) >> 35, (plane & np.uint64(0b1<<34)) >> 34, (plane & np.uint64(0b1<<33)) >> 33, (plane & np.uint64(0b1<<32)) >> 32
        , (plane & np.uint64(0b1<<31)) >> 31, (plane & np.uint64(0b1<<30)) >> 30, (plane & np.uint64(0b1<<29)) >> 29, (plane & np.uint64(0b1<<28)) >> 28
        , (plane & np.uint64(0b1<<27)) >> 27, (plane & np.uint64(0b1<<26)) >> 26, (plane & np.uint64(0b1<<25)) >> 25, (plane & np.uint64(0b1<<24)) >> 24
        , (plane & np.uint64(0b1<<23)) >> 23, (plane & np.uint64(0b1<<22)) >> 22, (plane & np.uint64(0b1<<21)) >> 21, (plane & np.uint64(0b1<<20)) >> 20
        , (plane & np.uint64(0b1<<19)) >> 19, (plane & np.uint64(0b1<<18)) >> 18, (plane & np.uint64(0b1<<17)) >> 17, (plane & np.uint64(0b1<<16)) >> 16
        , (plane & np.uint64(0b1<<15)) >> 15, (plane & np.uint64(0b1<<14)) >> 14, (plane & np.uint64(0b1<<13)) >> 13, (plane & np.uint64(0b1<<12)) >> 12
        , (plane & np.uint64(0b1<<11)) >> 11, (plane & np.uint64(0b1<<10)) >> 10, (plane & np.uint64(0b1<<9)) >> 9, (plane & np.uint64(0b1<<8)) >> 8
        , (plane & np.uint64(0b1<<7)) >> 7, (plane & np.uint64(0b1<<6)) >> 6, (plane & np.uint64(0b1<<5)) >> 5, (plane & np.uint64(0b1<<4)) >> 4
        , (plane & np.uint64(0b1<<3)) >> 3, (plane & np.uint64(0b1<<2)) >> 2, (plane & np.uint64(0b1<<1)) >> 1, (plane & np.uint64(0b1<<0)) >> 0]
    return np.concatenate(list(zip(*a)))

def sender(direccionIp, port, channels, depth, rate, chunk_size, levels, sent):
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(depth),
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk_size)

    udpEnviar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        sent.value += 1
        # Read from the sound card Chunk to CHUNK
        data = stream.read(chunk_size, exception_on_overflow=False)
        # Pass from type bytes to int16 using the numpy library
        array_In = np.frombuffer(data, dtype=np.int16)
        # Calculate the transform and store it in arrays in floats
        coeffs = pywt.wavedec(array_In, 'db1', level=levels)
        # Pass each component to 32-bit planes
        coeffs_planos = array_to_planos(coeffs) # Me devuelve una lista de 32, con 1024 muestras numericas entre 0 y 1
        # Send 32-bit planes
        enviar = []
        for i in range(0,32):
            plano_encode = encode(coeffs_planos[i])
            enviar = np.insert(plano_encode,0,(31-i))
            #print('ENVIAR -->', enviar)
            udpEnviar.sendto(enviar.tobytes(), (direccionIp, port))
            

def receiver(port, channels, depth, rate, chunk_size, levels, received):
    udpRecibir = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    direccion = ('0.0.0.0', port)
    udpRecibir.bind(direccion)

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(depth),
                    channels=channels,
                    rate=rate,
                    output=True,
                    frames_per_buffer=chunk_size)
    # Create buffer 
    buffer_planes = [0]*32
    while True:
        received.value += 1
        # receive 32 packages
        for i in range(0,32):
            plane, addr = udpRecibir.recvfrom(1025)
            plane = np.frombuffer(plane, dtype=np.uint64)
            # print("RECIVIR -->",plane)
            # Example: plane [32,0,0,0,0, ... ,1,0,1]
            index = plane[0]
            buffer_planes[index]=decode(plane[1:])
        # Pass each list of list in 32 planes to original subbands
        subbands = planos_to_array(buffer_planes, levels)
        # Calculate the inverse transform and store as int16
        # with the numpy library
        a_Out = pywt.waverec(subbands, 'db1').astype(np.int16)
        # Transmit to the sound card the wavelet array casted
        # to bytes
        stream.write(a_Out.tobytes())

def main():
    # Receive parameters for command line, if not, they have default parameters 
    parser = argparse.ArgumentParser(description = 'Arguments')
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--chunk_size', help='Chunk size in bytes.', type=int, default=1024)
    parser.add_argument('-r', '--rate', help='Sampling rate in samples/second.', type=int, default=44100)
    parser.add_argument('-n', '--nchannels', help='Number of channels.', type=int, default=1)
    parser.add_argument('-l', '--levels', help='Numbers of levels dwt.', type=int, default=5)
    parser.add_argument('-p', '--port', help='Listening port in the receiver and the destination port in the sender.', type=int, default=4443)
    parser.add_argument('-a', '--address', help='IP address of the receiver.', type=str, default='0.0.0.0')
    parser.add_argument('-d', '--depth', help='Depth in bytes of the samples of audio.', type=int, default=2)

    args = parser.parse_args()
    # Check if the level of dwt stay in range
    if (args.chunk_size < 2**args.levels):
        print('Numbers of levels dwt is not valid. The max levels dwt for chunk size', args.chunk, 'is', int(math.log(args.chunk,2)))
        quit()

    # Print input parameters 
    if __debug__:
        print('Chunk size:',args.chunk_size)
        print('Sampling rate:',args.rate)
        print('Numbers of channels:',args.nchannels)
        print('Numbers of levels of dwt:',args.levels)
        print('Port to send:',args.port)
        print('Address to send:',args.address)
        print('Sampling depth:', args.depth)

    # Number of chunks of data sent by the sender process
    sent_counter = multiprocessing.Value('i', 0)

    # Number of chunks of data received by the receiver process
    received_counter = multiprocessing.Value('i', 0)
        
    receiver_process = multiprocessing.Process(target=receiver, args=(args.port, args.nchannels, args.depth, args.rate, args.chunk_size, args.levels, received_counter))
    receiver_process.daemon = True

    sender_process = multiprocessing.Process(target=sender, args=(args.address, args.port, args.nchannels, args.depth, args.rate, args.chunk_size, args.levels, sent_counter))
    sender_process.daemon = True

    receiver_process.start()
    sender_process.start()

    #sender_process.join()
    while True:
        time.sleep(1)
        print(f'Sent {sent_counter.value} chunks, received {received_counter.value} chunks')
    input()

if __name__ == '__main__':
    main()
