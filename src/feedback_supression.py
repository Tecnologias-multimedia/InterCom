#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
'''Feedback supression (Acoustic Echo Cancellation).'''

import logging
import numpy as np
import minimal
import buffer
import math

minimal.parser.add_argument("--fir_length", type=int, default=8, 
                           help="Number of chunks in FIR filter")
minimal.parser.add_argument("--mu", type=float, default=0.01, 
                           help="LMS learning rate (0.001-0.1)")

class Feedback_Supression(buffer.Buffering):
    
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        
        self.played_chunk_history = []
    
        eco_delay = 0.02
        self.fir_length = math.ceil(eco_delay / self.chunk_time)
        self.fir_coeffs = np.zeros(self.fir_length, dtype=np.float32)
        self.mu = 1e-4           
        self.mu = minimal.args.mu
        
        logging.info(f"AEC LMS FIR: fir_length={self.fir_length}, mu={self.mu}")
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS

        # Obtener chunk a reproducir
        chunk = self.unbuffer_next_chunk()
        if chunk is None:
            chunk = self.zero_chunk

        # Guardar historial
        if len(self.played_chunk_history) > self.fir_length:
            self.played_chunk_history.pop(0)

        # Convertir a float32 en [-1,1]
        ADC_float = ADC.astype(np.float32) / 32768.0 #señal de micrófono actual
        played_chunks_float = [c.astype(np.float32) / 32768.0 for c in self.played_chunk_history]

        # Estimar eco
        echo_estimation = np.zeros_like(ADC_float)#crea array de 0 del tamaño de ADC
        for k in range(len(played_chunks_float)):
            echo_estimation += self.fir_coeffs[k] * played_chunks_float[-(k+1)] #convoluciona cada chunk multiplicándolo por el coeficiente

        # Error
        error = ADC_float - echo_estimation #a la señal actual le resta la estimación del eco 

        # LMS por chunk promedio (evita ValueError) calcula el coeficiente FIR para cada chunk para que aprenda automáticamente
        for k in range(len(played_chunks_float)):
            x = played_chunks_float[-(k+1)] #para ir de más reciente a menos 
            self.fir_coeffs[k] += self.mu * np.mean(error * x) / (np.mean(x**2)+1e-6)
        # Convertir error
        # r a int16 para poder reproducirlo sin problemas, evita errores de calculo 
        filtered_ADC = np.clip(error * 32768.0, -32768, 32767).astype(np.int16)

        # Atenuar chunk reproducido para reducir feedback directo
        chunk_to_play = (chunk.astype(np.float32) * 0.2).astype(np.int16)
        self.play_chunk(DAC, chunk_to_play)

        # Enviar señal limpia
        packed_chunk = self.pack(self.chunk_number, filtered_ADC)
        self.send(packed_chunk)



class Feedback_Supresssion__verbose(Feedback_Supression, buffer.Buffering__verbose):
    


    def __init__(self):
        super().__init__()
    


    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        if minimal.args.show_samples:
            self.show_recorded_chunk(ADC)
        
        super()._record_IO_and_play(ADC, DAC, frames, time, status)
        
        if minimal.args.show_samples:
            self.show_played_chunk(DAC)
        
        self.recorded_chunk = DAC
        self.played_chunk = ADC

try:
    import argcomplete
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
        intercom = Feedback_Supresssion__verbose()
    else:
        intercom = Feedback_Supression()
    
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()