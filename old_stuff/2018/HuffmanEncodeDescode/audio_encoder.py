#Programa implementa audio encoder Huffman y comprime archivo.
#La calidad default es de 100. Con valores mayores, reduce error quantization e incrementa calidad
#pero incrementa el bit rate.
#Para multi-channel audio, como stereo, encode los canales separadamente
#Comprime archivo a NombreArchivoIndicadoEnMetodo.acod

import sys
sys.path.append('./PythonPsychoacoustics')
from psyac_quantization import *
import numpy as np
import scipy.io.wavfile as wav 
import os
from dahuffman import HuffmanCodec
import pickle

def encodeAudio(fileName):
  audiofile=fileName
  print("Archivo audio=", audiofile)

  if len(sys.argv) ==3:
    quality=float(sys.argv[2])
  else:
    quality=100.0


  fs, x= wav.read(audiofile)

  try:
    channels=x.shape[1] #numero de canales, 2 para estereo(2 columnas en x)
  except IndexError:
    channels=1  # 1 para mono
    x=np.expand_dims(x,axis=1) #añade canales dimension 1

  print("Canales=", channels)
  N=1024 #numero de MDCY subbands
  nfilts=64  #numero de subbands en bark domain
  #Sine window:
  fb=np.sin(np.pi/(2*N)*(np.arange(int(1.5*N))+0.5))

  #Guarda en archivo pickle binario:
  #Quita extension del nombre del archivo
  name,ext=os.path.splitext(audiofile)
  #nueva extension .acod para el archivo encode 
  encfile=name+'.acod'
  print("Archivo comprimido:", encfile)
  totalbytes=0


  with open(encfile, 'wb') as codedfile: #abrimos archivo comprimido
    pickle.dump(fs,codedfile)
    pickle.dump(channels,codedfile)

    for chan in range(channels): #loop sobre canales
      print("Canal ", chan)
      #Calcular cuantificado en el dominio Bark y subbandas cuantificadas
      yq, y, mTbarkquant=MDCT_psayac_quant_enc(x[:,chan],fs,fb,N, nfilts,quality=quality)

      print("Huffman Coding")
      mTbarkquantflattened=np.reshape(mTbarkquant, (1,-1),order='F')
      mTbarkquantflattened=mTbarkquantflattened[0] #quitar dimension 0
      codecmTbarkquant=HuffmanCodec.from_data(mTbarkquantflattened)
      #Huffman tabla
      tablemTbarkquant=codecmTbarkquant.get_code_table()
      #Huffman encoded
      mTbarkquantc=codecmTbarkquant.encode(mTbarkquantflattened)

      #Calcula Huffman coder para cuantificado valor subbandas samples:
      yqflattened=np.reshape(yq,(1,-1),order='F')
      yqflattened=yqflattened[0] #quitar dimension 0
      codecyq=HuffmanCodec.from_data(yqflattened)
      #Huffman tabla
      tableyq=codecyq.get_code_table()
      #Huffman encoded
      yqc=codecyq.encode(yqflattened)
      
      pickle.dump(tablemTbarkquant ,codedfile) #factor de escala tabla
      pickle.dump(tableyq ,codedfile)  #subanda huffman tabla samples
      pickle.dump(mTbarkquantc ,codedfile) #Huffman coded factor de escala
      pickle.dump(yqc ,codedfile)  #Huffman coded subandas samples
      totalbytes+= len(tablemTbarkquant)+len(tableyq)+len(mTbarkquantc)+len(yqc)

  numsamples=np.prod(x.shape)
  print("Numero total de bytes=", totalbytes)
  print("Numero total de samples:", numsamples)
  print("bytes por sample=", totalbytes/numsamples)
