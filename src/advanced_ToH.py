import pyaudio
import numpy as np
import matplotlib.pyplot as plt


# Creación y reproducción de un sonido blanco (ruido)
def crerSonidoBlanco(frecuencia):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True)

    t = np.linspace(0, 1, 30000)
    datos = np.sin(2 * np.pi * frecuencia * t)

    stream.write(datos.astype(np.float32).tostring())

    stream.stop_stream()
    stream.close()
    p.terminate()



def main(frecuencia):

    crerSonidoBlanco(frecuencia)
    respuesta = input("¿Has oido algo? (si/no). El programa esta a {}Hz.". format(frecuencia))
    return respuesta == "si"


def bucleMedicionUmbral(frecuencia_maxima):

    resultados = []

    #Bucle iterativo para el muestreo del umbral de audición, es decir, si va escuchando el sonido o no
    for frecuencia in range(0, frecuencia_maxima, 1000):
        if main(frecuencia):
            resultados.append((frecuencia, decibelios))
        decibelios = 20 * np.log10(frecuencia / 1000)

    return resultados

def frecuencia_deseada():

    frecuencia = int(input("\n¿Hasta que frecuencia desea llegar? (Elija un valor entre 2000 y 20000)\n"))
    
    while frecuencia < 2000 or frecuencia > 20000:
        frecuencia = input("\nLa frecuencia debe ser un numero entero o estar entre 2000 y 20000\n")

    return frecuencia

# Ejecutar la función para medir el umbral de audición
resultados = bucleMedicionUmbral(frecuencia_deseada())

frecuencias, decibelios = zip(*resultados)

#Generación de la gráfica de resultados
plt.plot(frecuencias, decibelios)
plt.xlabel("Frecuencia (Hz)")
plt.ylabel("Decibelios (dB)")
plt.show()