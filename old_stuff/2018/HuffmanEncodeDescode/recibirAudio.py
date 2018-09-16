from socket import socket, error
import pyaudio
import wave
import pywt as wt
from ctypes import c_int32
from pyaudio import paInt16
from pyaudio import PyAudio
import sys
import time
import audio_decoder

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 5
VALORES = 32
ITERACIONESDWT = 9
NombreArchivoRecibido = "grabacionRecibido.acod"

#Reproduce archivo despues de ser decoded con Haffman
def playFile(audioFileDecoded):
    wf = wave.open(audioFileDecoded, 'rb')
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True)
    data = wf.readframes(CHUNK)

    while True:
        stream.write(data)
        data = wf.readframes(CHUNK)

    stream.stop_stream()
    stream.close()

    p.terminate()

#Espera recibir archivo encoded 
def recibirDatos():
    s = socket()
    s.bind(("localhost", 6030))
    s.listen(0)
    
    conn, addr = s.accept()
    f = open(NombreArchivoRecibido, "wb")
    
    while True:
        try:
            # Recibir datos del cliente.
            input_data = conn.recv(1024)
        except error:
            print("Error de lectura.")
            break
        else:
            if input_data:
                # Compatibilidad con Python 3.
                if isinstance(input_data, bytes):
                    end = input_data[0] == 1
                else:
                    end = input_data == chr(1)
                if not end:
                    # Almacenar datos.
                    f.write(input_data)
                else:
                    break
    
    print("El archivo se ha recibido correctamente.")
    f.close()

#Utilizamos 3 metodos: recibe archivo encoded, decode audio del archivo recibido y finalmente reproduce archivo decoded
if __name__ == "__main__":
    recibirDatos()
    time.sleep(3)
    audio_decoder.decodeAudio(NombreArchivoRecibido)
    time.sleep(1)
    playFile("grabacionRecibidodecodeFile.wav")
