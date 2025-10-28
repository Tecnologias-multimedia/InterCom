#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
'''Feedback supression (Acoustic Echo Cancellation).'''

import logging
import numpy as np
import minimal
import buffer

minimal.parser.add_argument("--delay_chunks", type=int, default=7, 
                           help="Delay in chunks for echo estimation")
minimal.parser.add_argument("--attenuation", type=float, default=0.5, 
                           help="Attenuation factor (0.0-0.99)")

class Feedback_Supression(buffer.Buffering):
    
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.played_chunk_history = []  # Lo que REPRODUCES (sale por altavoces)

        self.delay_in_chunks = minimal.args.delay_chunks
        self.attenuation = minimal.args.attenuation
        self.attenuation = min(max(self.attenuation, 0.0), 0.99)
 
        
        self.max_history = max(self.delay_in_chunks + 5, 30)
        
        logging.info(f"AEC: delay={self.delay_in_chunks} chunks "
                    f"({self.delay_in_chunks * self.chunk_time * 1000:.1f} ms), "
                    f"attenuation={self.attenuation}")
    
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS

    # Reproducir lo que llega desde red (o silencio)
        chunk = self.unbuffer_next_chunk()
        if chunk is None:
            chunk = self.zero_chunk
        self.play_chunk(DAC, chunk)

        # Guardar historial de salida
        self.played_chunk_history.append(chunk.copy())
        if len(self.played_chunk_history) > self.max_history:
            self.played_chunk_history.pop(0)

        # Estimar el eco según delay
        if len(self.played_chunk_history) >= self.delay_in_chunks:
            delayed_chunk = self.played_chunk_history[-self.delay_in_chunks]
        else:
            delayed_chunk = self.zero_chunk

        echo_estimation = self.attenuation * delayed_chunk

        # Cancelar el eco en la señal del micrófono
        filtered_ADC = ADC.astype(np.float32) - echo_estimation.astype(np.float32)
        filtered_ADC = np.clip(filtered_ADC, -32768, 32767).astype(np.int16)

        # Enviar la señal limpia
        packed_chunk = self.pack(self.chunk_number, filtered_ADC)
        self.send(packed_chunk)

        # 🔊 Reproducir también el micrófono procesado localmente (para verificar que se escucha)
        self.play_chunk(DAC, filtered_ADC)

class Feedback_Supression__verbose(Feedback_Supression, buffer.Buffering__verbose):
    
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
        intercom = Feedback_Supression__verbose()
    else:
        intercom = Feedback_Supression()
    
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()