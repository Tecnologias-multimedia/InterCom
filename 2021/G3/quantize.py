#!/usr/bin/env python
import zlib
import numpy as np
import struct
import time
import subprocess
import minimal
import buffer
import compress
import collections

#Global variables
tiempoChunk = 0.0
tiempoMedia = 0.0
delta = 1
lista = collections.deque(maxlen=50)


class BR_Control(compress.Compression):
    def __init__(self):

        super().__init__()
        
    def pack(self, chunk_number, chunk):
        #Cuantizamos
        quantized_chunk = BR_Control.quantize(chunk)
        #Comprimimos
        compressed_channel_0, compressed_channel_1 =  BR_Control.compressPack(quantized_chunk)
        #Empaquetamos
        packed_chunk = self.bufferPack(chunk_number,quantized_chunk,compressed_channel_0, compressed_channel_1)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        BR_Control.deltaVariable()
        chunk_number, len_compressed_channel_0 = self.bufferUnpack(packed_chunk)
        quantized_chunk = BR_Control.compressUnpack(packed_chunk, len_compressed_channel_0)
        chunk = BR_Control.dequantize(quantized_chunk)
        return chunk_number, chunk
    
    #Metodo antiguo
    def bandwidthTest():

        print("Testing connection bandwidth ...")
        destination = minimal.args.destination_address
        commandTp = "ping -c 2 -s 16 " + destination +" | tail -1| awk '{print $4}' | cut -d '/' -f 2"
        p1 = subprocess.Popen([commandTp], stdout = subprocess.PIPE, shell=True) 
        Tp = float(p1.communicate()[0].decode("utf-8"))
        commandTt = "ping -c 2 -s 65527 " + destination +" | tail -1| awk '{print $4}' | cut -d '/' -f 2"
        p2 = subprocess.Popen([commandTt], stdout = subprocess.PIPE, shell=True)  
        RTTmax = float(p2.communicate()[0].decode("utf-8"))
        Tt = ( RTTmax - Tp)/2
        b = (65537*8/Tt)/1000000
        print("Bandwidth = ", b ,"Mbit/s")
   
    def deltaVariable():
        global tiempoChunk
        global tiempoMedia
        global delta
        global lista

        #Calculamos el tiempo teorico que tarda cada chunk
        tiempoPorChunk = minimal.args.frames_per_chunk/minimal.args.frames_per_second + 0.0005 #
        
        end = time.time()
    
        chunkTiempo = (end - tiempoChunk)
        mediaTiempo = (end - tiempoMedia)
        tiempoChunk = end
       
        lista.append(chunkTiempo)

        if mediaTiempo >= 1:
            tiempoMedia = end
            media = sum(lista)/len(lista)
            #If necesario primeras ejecuciones
            if media > 10: 
                media = tiempoPorChunk
            print("\t\t\t\t\tMedia tiempoPorChunk = ", media, end='\r')
            diferencia = media-tiempoPorChunk
            
            if(diferencia) > 0:
                #print("Diferencia = ", diferencia, end='\r')
                delta += diferencia*7000 #7000 valor experiemental
            elif delta > 0 and delta-(delta*0.26) > 0 : 
                delta -= (delta*0.26)
            
            delta = int(round(delta))
            print(" Factor delta = ", delta*1.00, end='\r', flush=True)

    def quantize(packed_chunk):
        #Deadzone Quantization
        global delta
        k = (packed_chunk / delta).astype(np.int16)
        return k

    def dequantize(quantized_chunk):
        global delta
        y = delta * quantized_chunk
        return y

    def bufferPack(self,chunk_number, chunk, compressed_channel_0, compressed_channel_1):
        packed_chunk = struct.pack("!HH", chunk_number, len(compressed_channel_0)) + compressed_channel_0 + compressed_channel_1
        return packed_chunk

    def bufferUnpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        (chunk_number, len_compressed_channel_0) = struct.unpack("!HH", packed_chunk[:4])
        return chunk_number, len_compressed_channel_0

    def compressPack(quantized_chunk):
        channel_0 = quantized_chunk[:, 0].copy()
        channel_1 = quantized_chunk[:, 1].copy()
        compressed_channel_0 = zlib.compress(channel_0)
        compressed_channel_1 = zlib.compress(channel_1)
        return compressed_channel_0, compressed_channel_1

    def compressUnpack(packed_chunk,len_compressed_channel_0, dtype=minimal.Minimal.SAMPLE_TYPE):
        compressed_channel_0 = packed_chunk[4:len_compressed_channel_0+4]
        compressed_channel_1 = packed_chunk[len_compressed_channel_0+4:]
        channel_0 = zlib.decompress(compressed_channel_0)
        channel_0 = np.frombuffer(channel_0, dtype)
        channel_1 = zlib.decompress(compressed_channel_1)
        channel_1 = np.frombuffer(channel_1, dtype)   
        quantized_chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=dtype)
        quantized_chunk[:, 0] = channel_0[:]
        quantized_chunk[:, 1] = channel_1[:]      
        return quantized_chunk


if __name__ == "__main__": 
  
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Compression__verbose()
    else:
        #BR_Control.bandwidthTest()
        intercom = BR_Control()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
