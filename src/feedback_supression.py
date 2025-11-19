from collections import deque
import numpy as np
import minimal
import buffer
import logging

def to_mono_float32(arr):
    arr = arr.astype(np.float32)
    if arr.ndim == 1:
        return arr / 32768.0
    elif arr.ndim == 2:
        return arr.mean(axis=1) / 32768.0
    else:
        raise ValueError(f"Formato de audio no soportado: shape={arr.shape}")

class Feedback_Supression(buffer.Buffering):
    """AEC NLMS con aprendizaje gradual y supresión de eco segura."""

    def __init__(self):
        super().__init__()
        self.fir_length = 128
        self.fir_coeffs = np.zeros(self.fir_length, dtype=np.float32)
        self.mu_base = 0.002        # muy conservador para evitar feedback
        self.eps = 1e-6
        self.played_chunk_history = deque(maxlen=self.fir_length)
        self.fade_in_chunks = 50 * self.CHUNK_NUMBERS

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS

        # Obtener chunk reproducido de forma segura
        chunk = self.unbuffer_next_chunk()
        if chunk is None:
            chunk = self.zero_chunk

        # Guardar historial
        self.played_chunk_history.append(chunk.copy())
        while len(self.played_chunk_history) < self.fir_length:
            self.played_chunk_history.appendleft(np.zeros_like(chunk))

        ADC_float = to_mono_float32(ADC)
        played_chunks_float = [to_mono_float32(c) for c in self.played_chunk_history]

        # Estimación del eco
        echo_estimation = sum(c * coeff for c, coeff in zip(reversed(played_chunks_float), self.fir_coeffs))
        error = ADC_float - echo_estimation

        # Fade-in gradual de mu
        fade_in_factor = min(1.0, self.chunk_number / self.fade_in_chunks)

        rms_error = np.sqrt(np.mean(error**2)) + 1e-9
        rms_voice = np.sqrt(np.mean(ADC_float**2)) + 1e-9

        # NLMS con aprendizaje dinámico seguro
        for k in range(self.fir_length):
            x = played_chunks_float[-(k+1)]
            rms_x = np.sqrt(np.mean(x**2)) + 1e-9
            x_norm = x / rms_x
            energy = np.dot(x_norm, x_norm) + self.eps

            mu_eff = self.mu_base * fade_in_factor * (1 + rms_error/rms_voice)
            mu_eff = min(mu_eff / energy, 0.015)
            crosscorr = np.dot(x_norm, error)
            self.fir_coeffs[k] += mu_eff * crosscorr
            self.fir_coeffs[k] = np.clip(self.fir_coeffs[k], -0.5, 0.5)

        # Normalización del error para evitar saturación
        max_amp = 0.4
        if rms_error > max_amp:
            error = error * (max_amp / rms_error)

        filtered_ADC_stereo = np.column_stack([error, error])
        filtered_ADC_stereo = (filtered_ADC_stereo * 32767).astype(np.int16)

        # Atenuación inicial segura + fade-in gradual
        atten_factor = 0.1 + 0.9 * fade_in_factor
        chunk_to_play = (chunk.astype(np.float32) * atten_factor).astype(np.int16)

        self.play_chunk(DAC, chunk_to_play)
        packed = self.pack(self.chunk_number, filtered_ADC_stereo)
        self.send(packed)

class Feedback_Supression__verbose(Feedback_Supression, buffer.Buffering__verbose):
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        if minimal.args.show_samples:
            self.show_recorded_chunk(ADC)
        super()._record_IO_and_play(ADC, DAC, frames, time, status)
        if minimal.args.show_samples:
            self.show_played_chunk(DAC)
        self.recorded_chunk = DAC
        self.played_chunk = ADC

if __name__ == "__main__":
    try:
        import argcomplete
    except ImportError:
        logging.warning("Unable to import argcomplete (optional)")

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
