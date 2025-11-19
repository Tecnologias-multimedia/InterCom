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
    """AEC NLMS seguro con aprendizaje gradual y control de volumen."""

    def __init__(self):
        super().__init__()
        self.fir_length = 128
        self.fir_coeffs = np.zeros(self.fir_length, dtype=np.float32)
        self.mu_base = 0.002
        self.eps = 1e-9
        self.chunk_history = deque(maxlen=self.fir_length)
        self.fade_in_chunks = 50 * self.CHUNK_NUMBERS

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS

        # --- Obtener chunk reproducido ---
        chunk = self.unbuffer_next_chunk()
        if chunk is None:
            chunk = self.zero_chunk

        # --- Convertir a mono para AEC ---
        mono_chunk = to_mono_float32(chunk)
        self.chunk_history.append(mono_chunk)

        # Rellenar con ceros si historial incompleto
        while len(self.chunk_history) < self.fir_length:
            self.chunk_history.appendleft(np.zeros_like(mono_chunk))

        ADC_float = to_mono_float32(ADC)

        # --- Estimación de eco con FIR (convolución simple) ---
        echo_estimation = np.zeros_like(ADC_float)
        history_list = list(self.chunk_history)
        for k in range(self.fir_length):
            # Ajustamos tamaño por si el chunk es más largo que ADC_float
            L = min(len(ADC_float), len(history_list[k]))
            echo_estimation[:L] += self.fir_coeffs[k] * history_list[k][:L]

        # --- Error ---
        error = ADC_float[:len(echo_estimation)] - echo_estimation

        # --- Fade-in de mu ---
        fade_in_factor = min(1.0, self.chunk_number / self.fade_in_chunks)
        rms_error = np.sqrt(np.mean(error**2)) + 1e-9
        rms_voice = np.sqrt(np.mean(ADC_float**2)) + 1e-9

        # --- NLMS seguro ---
        for k in range(self.fir_length):
            x = history_list[k][:len(error)]
            energy = np.dot(x, x) + self.eps
            mu_eff = min(self.mu_base * fade_in_factor * (1 + rms_error / rms_voice) / energy, 0.015)
            self.fir_coeffs[k] += mu_eff * np.dot(x, error)
        self.fir_coeffs = np.clip(self.fir_coeffs, -0.5, 0.5)

        # --- Normalizar error ±0.4 ---
        max_amp = 0.4
        if rms_error > max_amp:
            error *= max_amp / rms_error

        # --- Salida estéreo ---
        filtered_ADC_stereo = np.column_stack([error, error])
        filtered_ADC_stereo = (filtered_ADC_stereo * 32767).astype(np.int16)

        # --- Atenuación segura ---
        atten_factor = 0.1 + 0.9 * fade_in_factor
        final_volume = 1.0
        chunk_to_play = np.clip(chunk.astype(np.float32) * atten_factor * final_volume, -32768, 32767)

        # --- Ajustar tamaño exacto ---
        channels = minimal.args.number_of_channels
        frames = minimal.args.frames_per_chunk
        if chunk_to_play.size != frames * channels:
            chunk_to_play = np.resize(chunk_to_play, (frames, channels))
        else:
            chunk_to_play = chunk_to_play.reshape(frames, channels)

        self.play_chunk(DAC, chunk_to_play)

        packed = self.pack(self.chunk_number, filtered_ADC_stereo)
        self.send(packed)


class Feedback_Supression__verbose(Feedback_Supression, buffer.Buffering__verbose):
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        if getattr(minimal.args, "show_samples", False):
            self.show_recorded_chunk(ADC)
        super()._record_IO_and_play(ADC, DAC, frames, time, status)
        if getattr(minimal.args, "show_samples", False):
            self.show_played_chunk(DAC)
        self.recorded_chunk = DAC
        self.played_chunk = ADC

if __name__ == "__main__":
    try:
        import argcomplete
    except ImportError:
        logging.warning("Unable to import argcomplete (optional)")

    # Parsear argumentos
    minimal.args = minimal.parser.parse_known_args()[0]
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")

    # Elegir clase según verbose o no
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
