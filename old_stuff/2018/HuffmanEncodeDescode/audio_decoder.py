#Program to decode the encoded audio signal in *.acod
#usage: python3 audio_decoder.py audiofile.acod
#Writes the decoded audio signal in .wav format in file audiofilerek.wav
#For multichannel signals it uses separate decoding.
#Gerald Schuller, June 2018

import sys
sys.path.append('./PythonPsychoacoustics')
from psyac_quantization import *
import numpy as np
import scipy.io.wavfile as wav 
import os
from dahuffman import HuffmanCodec
import pickle


def decodeAudio(audioFileEncoded):
   encfile=audioFileEncoded
   print("Archivo encoded=",encfile)

   N=1024 #numero de MDCT subbands
   nfilts=64  #numero de subbands en bark domain
   #Sine window:
   fb=np.sin(np.pi/(2*N)*(np.arange(int(1.5*N))+0.5))
   #abrir archivo binario pickle:
   #Quita extension del nombre del archivo 
   name,ext=os.path.splitext(encfile)
   #nuevo nombre y extension para el archivo decoded
   decfile=name+'decodeFile.wav'
   print("Decoded Archivo:", decfile)

   with open(encfile, 'rb') as codedfile:
      fs=pickle.load(codedfile)
      channels=pickle.load(codedfile)
      print("Fs=", fs, "Canales=", channels, )
      
      for chan in range(channels): #loop sobre canales:
         print("Canal ", chan)
         tablemTbarkquant=pickle.load(codedfile) #factor escala huffman tabla
         tableyq=pickle.load(codedfile)  #subanda huffman tabla samples
         mTbarkquantc=pickle.load(codedfile) #Huffman coded factor de escala
         yqc=pickle.load(codedfile)  #Huffman coded subandas samples

         #Huffman decoder para factor escala
         codecmTbarkquant=HuffmanCodec(code_table=tablemTbarkquant, check=False)
         #Huffman decoded factor escala
         mTbarkquantflattened=codecmTbarkquant.decode(mTbarkquantc)
         #reshape para volver a una matriz con columnas de length nfilts
         mTbarkquant=np.reshape(mTbarkquantflattened, (nfilts,-1),order='F')

         #Huffman decoder para subandas samples
         codecyq=HuffmanCodec(code_table=tableyq, check=False)
         #Huffman decode subandas samples
         yqflattened=codecyq.decode(yqc)
         #reshape para volver a una matriz con columnas length
         yq=np.reshape(yqflattened, (N,-1),order='F')
         #dequantizar y calcular MDCT and compute MDCT sintesis
         xrek, mT, ydeq = MDCTsyn_dequant_dec(yq, mTbarkquant, fs, fb, N, nfilts)
         if chan==0:
            x=xrek
         else:
            x=np.vstack((x,xrek))
   x=np.clip(x.T,-2**15,2**15-1)
   #Escribe señal decoded a un archivo wav file
   wav.write(decfile,fs,np.int16(x))

