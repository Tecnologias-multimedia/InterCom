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
    """AEC NLMS con VAD basado en frecuencia dominante y SNR, preprocesado HP y sustracción de ruido, logs completos."""

    def __init__(self):
        super().__init__()
        self.fir_length = 128
        self.fir_coeffs = np.zeros(self.fir_length, dtype=np.float32)

        self.mu_base = 0.002
        self.mu_max = 0.005
        self.eps = 1e-9

        self.chunk_history = deque(maxlen=self.fir_length)

        self.fade_in_chunks = 50 * self.CHUNK_NUMBERS
        self.chunk_number = 0

        # --- Parámetros del entorno ---
        self.fs = getattr(minimal.args, "sample_rate", 48000)
        self.frames_per_chunk = getattr(minimal.args, "frames_per_chunk", 1024)

        # --- High-pass first order ---
        self.hp_cutoff = 80.0
        rc = 1.0 / (2 * np.pi * self.hp_cutoff)
        dt = 1.0 / self.fs
        self.hp_alpha = rc / (rc + dt)
        self.hp_prev_x = 0.0
        self.hp_prev_y = 0.0

        # --- Estimador de ruido estacionario ---
        self.noise_beta = 0.995
        self.noise_profile = np.zeros(self.frames_per_chunk, dtype=np.float32)

        # --- FFT thresholds ---
        self.fft_min_energy = 1e-6

    # ===========================================================
    # PREPROCESADO
    # ===========================================================
    def _highpass_chunk(self, x):
        """High-pass primer orden con continuidad entre chunks."""
        y = np.empty_like(x)
        prev_x = self.hp_prev_x
        prev_y = self.hp_prev_y
        a = self.hp_alpha
        for i, xi in enumerate(x):
            yi = a * (prev_y + xi - prev_x)
            y[i] = yi
            prev_x = xi
            prev_y = yi
        self.hp_prev_x = prev_x
        self.hp_prev_y = prev_y
        return y

    def _update_noise_profile_and_subtract(self, x):
        """Actualiza noise_profile con EMA lenta y devuelve x - noise_est."""
        if len(self.noise_profile) != len(x):
            self.noise_profile = np.zeros_like(x)
        self.noise_profile = self.noise_beta * self.noise_profile + (1.0 - self.noise_beta) * x
        return x - self.noise_profile

    def _dominant_freq(self, x):
        """Devuelve frecuencia dominante y magnitud del chunk."""
        N = len(x)
        if N <= 0:
            return 0.0, 0.0
        X = np.fft.rfft(x * np.hanning(N))
        mags = np.abs(X)
        if np.sum(mags**2) < self.fft_min_energy:
            return 0.0, 0.0
        freqs = np.fft.rfftfreq(N, d=1.0/self.fs)
        idx = np.argmax(mags)
        return float(freqs[idx]), float(mags[idx])

    # ===========================================================
    # PROCESAMIENTO PRINCIPAL
    # ===========================================================
    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number += 1

        # --- Chunk a reproducir ---
        chunk = self.unbuffer_next_chunk()
        chunk = chunk if chunk is not None else self.zero_chunk
        mono_chunk = to_mono_float32(chunk)
        self.chunk_history.append(mono_chunk)
        while len(self.chunk_history) < self.fir_length:
            self.chunk_history.appendleft(np.zeros_like(mono_chunk))

        ADC_float = to_mono_float32(ADC)

        # --- Preprocesado ---
        ADC_hp = self._highpass_chunk(ADC_float)
        ADC_denoised = self._update_noise_profile_and_subtract(ADC_hp)
        dom_freq, dom_mag = self._dominant_freq(ADC_hp)

        # --- Estimación de eco FIR ---
        echo_est = np.zeros_like(ADC_denoised)
        history = list(self.chunk_history)
        for k in range(self.fir_length):
            x = history[k]
            L = min(len(ADC_denoised), len(x))
            echo_est[:L] += self.fir_coeffs[k] * x[:L]

        error = ADC_denoised - echo_est

        # --- RMS y SNR ---
        rms_error = np.sqrt(np.mean(error**2)) + 1e-9
        rms_voice = np.sqrt(np.mean(ADC_denoised**2)) + 1e-9
        noise_rms = np.sqrt(np.mean(self.noise_profile**2)) + 1e-12
        snr = rms_voice / noise_rms

        fade_in_factor = min(1.0, self.chunk_number / self.fade_in_chunks)

        # --- VAD basado en frecuencia dominante y SNR ---
        voice_detected = (dom_freq > 180.0) and (snr > 15.0)

        # --- NLMS si hay voz ---
        mu_used = []
        if voice_detected:
            for k in range(self.fir_length):
                x = history[k][:len(error)]
                energy = np.dot(x, x) + self.eps
                mu_eff = min(self.mu_base * fade_in_factor / energy, self.mu_max)
                self.fir_coeffs[k] += mu_eff * np.dot(x, error)
                mu_used.append(mu_eff)

        # --- Decaimiento anti-drift ---
        self.fir_coeffs *= 0.9997
        self.fir_coeffs = np.clip(self.fir_coeffs, -0.5, 0.5)

        # --- Normalización salida ---
        if rms_error > 0.4:
            error *= 0.4 / rms_error
        filtered_ADC_stereo = np.column_stack([error, error])
        filtered_ADC_stereo = (filtered_ADC_stereo * 32767).astype(np.int16)

        atten_factor = 0.1 + 0.9 * fade_in_factor
        manual = 1.5
        chunk_to_play = np.clip(chunk.astype(np.float32) * atten_factor * manual, -32768, 32767)

        # Ajuste de forma
        channels = minimal.args.number_of_channels
        frames = minimal.args.frames_per_chunk
        if chunk_to_play.size != frames * channels:
            chunk_to_play = np.resize(chunk_to_play, (frames, channels))
        else:
            chunk_to_play = chunk_to_play.reshape(frames, channels)

        self.play_chunk(DAC, chunk_to_play)

        # --- Logs ---
        fir_energy = np.sum(self.fir_coeffs**2)
        noise_profile_rms = np.sqrt(np.mean(self.noise_profile**2)) + 1e-12
        print("──────────── ITERACIÓN AEC ────────────")
        print(f"Chunks procesados:        {self.chunk_number}")
        print(f"Fade-in factor:           {fade_in_factor:.6f}")
        print(f"RMS voz (mic, preproc):   {rms_voice:.6f}")
        print(f"RMS error:                {rms_error:.6f}")
        print(f"SNR:                      {snr:.2f}")
        print(f"Actividad de voz:         {voice_detected}")
        print(f"Promedio μ aplicado:      {np.mean(mu_used) if mu_used else 0:.6e}")
        print(f"Energía FIR:              {fir_energy:.6f}")
        print(f"Atenuación playback:      {atten_factor:.3f}")
        print(f"Noise profile RMS:        {noise_profile_rms:.6e}")
        print(f"Dominant freq (HP input): {dom_freq:.1f} Hz (mag {dom_mag:.3e})")
        print("────────────────────────────────────────")

        # --- Enviar paquete ---
        self.send(self.pack(self.chunk_number, filtered_ADC_stereo))

class Feedback_Supression__verbose(Feedback_Supression, buffer.Buffering__verbose):
    """Versión verbose con visualización de chunks grabados y reproducidos."""
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

    minimal.args = minimal.parser.parse_known_args()[0]
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")

    # Elegir clase según verbose
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
