#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
'''Feedback supression (Acoustic Echo Cancellation) – NLMS estable con fade-in y salida estéreo segura.'''

import logging
import numpy as np
import minimal
import buffer

# Argumentos
minimal.parser.add_argument("--fir_length", type=int, default=8,
                           help="Number of chunks in FIR filter")
minimal.parser.add_argument("--mu", type=float, default=0.03,  # menos agresivo
                           help="NLMS learning rate (0.0–1.0)")
minimal.parser.add_argument("--eps", type=float, default=1e-6,
                           help="Small value to avoid division by zero")

# ---------------------------------------------------------
# Convierte cualquier señal int16 a MONO float32 [-1,1]
# ---------------------------------------------------------
def to_mono_float32(arr):
    arr = arr.astype(np.float32)
    if arr.ndim == 1:
        return arr / 32768.0
    elif arr.ndim == 2:
        return arr.mean(axis=1) / 32768.0
    else:
        raise ValueError("Formato de audio no soportado: shape=" + str(arr.shape))

# ===================================================================
#                         AEC NLMS (ESTABLE CON FADE-IN)
# ===================================================================
class Feedback_Supression(buffer.Buffering):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

        self.played_chunk_history = []
        self.fir_length = minimal.args.fir_length
        self.fir_coeffs = np.zeros(self.fir_length, dtype=np.float32)
        self.mu = minimal.args.mu
        self.eps = minimal.args.eps

        logging.info(f"AEC NLMS estable: fir_length={self.fir_length}, mu={self.mu}, eps={self.eps}")

    # -----------------------------------------------------------------------
    #                         CALLBACK PRINCIPAL
    # -----------------------------------------------------------------------
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):

        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS

        chunk = self.unbuffer_next_chunk()
        if chunk is None:
            chunk = self.zero_chunk

        # Guardar historial
        self.played_chunk_history.append(chunk.copy())
        if len(self.played_chunk_history) > self.fir_length:
            self.played_chunk_history.pop(0)

        # Rellenar con ceros si faltan chunks
        if len(self.played_chunk_history) < self.fir_length:
            missing = self.fir_length - len(self.played_chunk_history)
            zero_chunk = np.zeros_like(chunk)
            self.played_chunk_history = [zero_chunk] * missing + self.played_chunk_history

        # Convertir todo a MONO float32
        ADC_float = to_mono_float32(ADC)
        played_chunks_float = [to_mono_float32(pc) for pc in self.played_chunk_history]

        # -------------------------------------------------------------
        # Estimación del eco (FIR por bloques)
        # -------------------------------------------------------------
        echo_estimation = np.zeros_like(ADC_float, dtype=np.float32)
        for k in range(self.fir_length):
            echo_estimation += self.fir_coeffs[k] * played_chunks_float[-(k + 1)]

        # Error
        error = ADC_float - echo_estimation

        # -------------------------------------------------------------
        # Fade-in NLMS (evita picos al inicio)
        # -------------------------------------------------------------
        fade_in_factor = min(1.0, self.chunk_number / (10 * self.CHUNK_NUMBERS))  # primeros 10 chunks
        mu_eff = self.mu * fade_in_factor

        # NLMS update
        for k in range(self.fir_length):
            x = played_chunks_float[-(k + 1)]
            energy = np.dot(x, x) + self.eps
            crosscorr = np.dot(x, error)
            self.fir_coeffs[k] += (mu_eff * crosscorr) / energy

        # -------------------------------------------------------------
        # Señal filtrada → normalizar ±0.5 para salida stereo segura
        # -------------------------------------------------------------
        filtered_ADC_float = np.clip(error, -0.5, 0.5)
        filtered_ADC_stereo = np.column_stack([filtered_ADC_float, filtered_ADC_float])
        filtered_ADC_stereo = (filtered_ADC_stereo * 32767).astype(np.int16)

        # Atenuar el chunk reproducido para reducir feedback
        chunk_to_play = (chunk.astype(np.float32) * 0.4).astype(np.int16)
        self.play_chunk(DAC, chunk_to_play)

        # Enviar señal limpia
        packed = self.pack(self.chunk_number, filtered_ADC_stereo)
        self.send(packed)

# ===================================================================
# VERSIÓN VERBOSE
# ===================================================================
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

# ===================================================================
# MAIN
# ===================================================================
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
