#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

# Restar al chunk capturado el chunk recibido, en el dominio de Fourier.

# Probar a comprimir (logaritmicamente) la salida por los altavoces con una ganancia proporcional al parecido entre lo que sale por los altavoces (lo que llega a través de la red) y lo que captura el micrófono. Probado y no funciona bien porque el logaritmo amplifica el ruido de fondo.


'''Feedback supression (template).'''

import logging
import numpy as np

import minimal
import buffer
        
class Feedback_Supression(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.chunk_to_play = np.empty_like(self.zero_chunk)
        self.maxx = 1.0

    # Si hablamos, no escuchamos. Si no escuchamos, podemos atenuar lo
    # recibido.
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        packed_chunk = self.pack(self.chunk_number, ADC)
        self.send(packed_chunk)
        received_chunk = self.unbuffer_next_chunk()
        #chunk_to_play = (32768/np.max(ADC))*received_chunk
        a = np.fft.rfft(ADC[:,0]) # ADC = m + s
        b = np.sqrt(a.real*a.real + a.imag*a.imag) / minimal.args.frames_per_chunk + 1
        c0 = np.fft.rfft(received_chunk[:,0])
        c1 = np.fft.rfft(received_chunk[:,1])
        s = b.real*b.real + b.imag*b.imag
        #c0 /= (0.1* b)
        #c1 /= (0.1* b)
        c0 = np.where(s>np.max(ADC)*0.3, c0*0.3, c0)
        c1 = np.where(s>np.max(ADC)*0.3, c1*0.3, c1)
        d0 = np.fft.irfft(c0)
        d1 = np.fft.irfft(c1)
        self.chunk_to_play[:,0] = d0
        self.chunk_to_play[:,1] = d1
        self.play_chunk(DAC, self.chunk_to_play)
        print(".")

    def __old__():
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        packed_chunk = self.pack(self.chunk_number, ADC)
        self.send(packed_chunk)
        received_chunk = self.unbuffer_next_chunk()
        #print(chunk.shape)
        #self.recorded_chunk[:, 0] = ADC[:, 0]
        #self.recorded_chunk[:, 1] = ADC[:, 1]
        self.recorded_chunk = ADC
        #self.empty_chunk[:, 0] = 50*np.log(1+chunk[:, 0])
        #self.empty_chunk[:, 1] = 50*np.log(1+chunk[:, 1])
        self.maxx = 0.5*(32767/(np.max(ADC)+1)) + 0.5*self.maxx
        self.maxx = 1+1/self.maxx
        #if self.maxx > 0.5:
        #    self.maxx = 0.1
        #chunk_to_play = self.maxx*received_chunk
        chunk_to_play = (self.maxx*100/np.max(ADC))*received_chunk
        #print(np.max(chunk_to_play))
        print(self.maxx)
        self.play_chunk(DAC, chunk_to_play)

    def _old_(self):
        mean_0 = np.mean(ADC[:, 0])
        mean_1 = np.mean(ADC[:, 1])
        mean_ADC_0 = mean_0 + ADC[:, 0]
        mean_ADC_1 = mean_1 + ADC[:, 1]
        gain = 1000
        gain_0 = (gain * np.abs(mean_0)/32768)
        gain_1 = (gain * np.abs(mean_1)/32768)
        #log_mean_ADC_0 = np.log(1 + gain_0*mean_ADC_0)
        log_mean_ADC_0 = np.log(1 + 0.1*mean_ADC_0)
        #log_mean_ADC_1 = np.log(1 + gain_1*mean_ADC_1)
        log_mean_ADC_1 = np.log(1 + 0.1*mean_ADC_1)
        channel_0 = (log_mean_ADC_0 - mean_0).astype(np.int16)
        channel_1 = (log_mean_ADC_1 - mean_1).astype(np.int16)
        #print(ADC[:, 0], mean_0, gain_0, channel_0)
        #self.empty_chunk[:, 0] = ADC[:, 0] - channel_0
        #self.empty_chunk[:, 0] = channel_0
        #self.empty_chunk[:, 0] = np.log(1+0.1*ADC[:, 0])
        self.empty_chunk[:, 0] = ADC[:, 0]
        #self.empty_chunk[:, 1] = ADC[:, 1] - channel_1
        #self.empty_chunk[:, 1] = channel_1
        #self.empty_chunk[:, 1] = np.log(1+0.1*ADC[:, 1])
        self.empty_chunk[:, 1] = ADC[:, 1]
        DAC[...] = self.empty_chunk
        print(".")

class Feedback_Supression__verbose(Feedback_Supression, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")
    minimal.args = minimal.parser.parse_known_args()[0]

    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = Feedback_Supression__verbose()
    else:
        intercom = Feedback_Supression()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
       intercom.print_final_averages()
