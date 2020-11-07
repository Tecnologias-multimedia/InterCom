# Tecnologías multimedia
Proyecto de tecnologías multimedia consistente en un interfono cliente/servidor que empaqueta trozos de audio, los envía por UDP y los reproduce con la menor latencia posible.

## Guía de buenas prácticas utilizadas

El uso de buenas prácticas permite a los diferentes usuarios ya sean o no parte de nuestro proyecto tener una mayor compresión sobre su contenido evitando rompeduras de cabeza innecesarias.

En python existe una guía de buenas practicas, denominada [PEP-0008](https://www.python.org/dev/peps/pep-0008). Esta define por convenio el estilo que se ha de usar para la asignación de nombres a los métodos, la documentación, la importación de clases, etc...


### Clases
Las clases deben utilizar por convención el formato PascalCase (o UpperCamelCase), palabras que siempre comienzan con mayusculas. [PEP-0008](https://www.python.org/dev/peps/pep-0008/#class-names).

```python
class UdpReceiver():
    pass
```


### Métodos y variables
Los nombres de los métodos y las instancias de las variables usan snake_case, `_` (barrabaja) entre las palabras, siendo el número de estas las necesarias para su comprensión. En el caso de los métodos y varibales no públicas se usará una única `_`. Generalmente solo se usarán dos `__` para evitar conflictos de nombres con los atributos de las clases que han sido creadas para ser subclases. 
```python
def disponible_args():
    NUMBER_OF_CHANNELS = 2
```


### Docstring
La creación de documentación usa otro convenio definido por [PEP 257](https://www.python.org/dev/peps/pep-0257/).
El convenio define las lineas de documentación como "docstrings" y deben de ser escritos para todo el contenido publico como módulos, funciones, clases y métodos, en el caso del contenido no público no será necesario, pero sí será necesario escribir una linea explicando qué hace el método. 

Todo el contenido que se utilice como "docstring" debe aparecer debajo de la linea "def", el formato para hacerlo es usar """triples comillas""". Existen dos formas de usar "docstring":
-   En una sola linea
-   En varias lineas: Al inicio del "docstringt" aparecera una linea de resumen siguiendo las 3 comillas o en la siguiente linea, pero tras ella se dejara una linea en blanco, seguido por una descripción más elaborada.



[1] PEP 257. <https://www.python.org/dev/peps/pep-0257/>
[2] PEP 8. <https://www.python.org/dev/peps/pep-0008/>

```python
def play(self, chunk, stream):
        """Write samples to the stream.

            Parameters
            ----------
            chunk : buffer
                A buffer of interleaved samples. The buffer contains
                samples in the format specified by the *dtype* parameter
                used to open the stream, and the number of channels
                specified by *channels*.

            stream : sd.RawStream
                Raw stream for playback and recording.
            """
        stream.write(chunk)
```
![Ejemplo de uso de docstring](https://github.com/RaquelGG/TM/blob/master/otros/docstring.gif)

## Cosas a destacar sobre la implementación
Se ha usado la biblioteca [`sounddevice`](https://python-sounddevice.readthedocs.io/en/0.4.1/) para la captura y reproducción del audio.

### Hilos
El programa tiene 2 tareas principales e independientes:
1. Grabar audio y enviarlo por internet.
1. Recibir audio de la red y reproducirlo.

Usamos la biblioteca [`threading`](https://docs.python.org/3.8/library/threading.html) que construye interfaces de subprocesamiento de nivel superior sobre el módulo `_thread` de nivel inferior.

```python
import threading
... 
clientT = threading.Thread(target=intercom.client)
clientT.start()
```

### RawInputStream y RawOutputStream
[`RawInputStream`](https://python-sounddevice.readthedocs.io/en/0.4.1/api/raw-streams.html#sounddevice.RawInputStream) gestiona los dispositivos de entrada de nuestro dispositivo y [`RawOutputStream`](https://python-sounddevice.readthedocs.io/en/0.4.1/api/raw-streams.html#sounddevice.RawOutputStream) los de salida.
Son “raw” (crudo en inglés) porque envían y reciben datos directamente en buffers de python, en lugar de utilizar `numpy`.
```python
stream = sd.RawInputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16')
...
stream = sd.RawOutputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16')
```
Como tratamos la entrada y la salida totalmente por separado, no es necesario realizar exclusión mutua.

