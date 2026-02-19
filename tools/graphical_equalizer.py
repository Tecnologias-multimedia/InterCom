import numpy as np
import sounddevice as sd
import soundfile as sf
import pywt
import json
import os
import tkinter as tk  # sudo pacman -S tk
from tkinter import ttk, filedialog, messagebox
from scipy.fft import dct, idct

# --- Configuration ---
SAMPLE_RATE = 44100
BLOCK_SIZE = 4096
NUM_BANDS = 32
WAVELET_LEVEL = int(np.log2(NUM_BANDS))

DEFAULT_WAV_FAMILY = 'db'
DEFAULT_WAV_FILTER = 'db5'
MAX_SLIDER_GAIN = 1.0 

BASE_NOISE_VOL = 0.2
BASE_TONAL_VOL = 0.05
BASE_FILE_VOL = 0.8 

# --- FREQUENCY CALCULATIONS ---
nyquist = SAMPLE_RATE / 2
bandwidth = nyquist / NUM_BANDS
end_freqs = np.array([(i + 1) * bandwidth for i in range(NUM_BANDS)])
center_freqs = np.array([(i * bandwidth) + (bandwidth / 2) for i in range(NUM_BANDS)])

def ToH_model(f):
    f = np.maximum(f, 1e-6) 
    term1 = 3.64 * (f / 1000) ** (-0.8)
    term2 = -6.5 * np.exp(-0.6 * ((f / 1000 - 3.3) ** 2))
    term3 = 10 ** (-3) * (f / 1000) ** 4
    return term1 + term2 + term3

toh_raw = ToH_model(center_freqs)
t_min, t_max = np.min(toh_raw), np.max(toh_raw)
toh_normalized = (toh_raw - t_min) / (t_max - t_min) if t_max > t_min else np.zeros_like(toh_raw)
INITIAL_TOH_GAINS = ((1.0 - toh_normalized) * MAX_SLIDER_GAIN).astype(np.float32)

class AudioEQApp:
    def __init__(self, root):
        self.root = root
        self.root.title("32-Band Audio Equalizer")
        self.root.geometry("1400x700")
        self.root.configure(padx=10, pady=10)

        # --- Audio State ---
        self.gains = np.copy(INITIAL_TOH_GAINS)
        self.band_active = np.ones(NUM_BANDS, dtype=bool)
        self.band_variances = np.zeros(NUM_BANDS, dtype=np.float32)
        
        self.master_variance = 0.0
        self.master_peak = 0.0
        self.smoothed_vals = np.zeros(NUM_BANDS, dtype=np.float32)
        self.smoothed_master = 0.0
        self.DECAY_FACTOR = 0.85

        self.global_volume = 1.0 
        self.mix_noise = 0.0
        self.mix_tone = 0.0
        self.mix_file = 1.0
        self.passthrough_mode = False 
        self.process_method = tk.StringVar(value='Wavelet')
        self.current_wavelet = DEFAULT_WAV_FILTER
        
        self.file_data = None
        self.file_play_head = 0
        self.phases = np.zeros(NUM_BANDS)
        self.audio_stream = None
        
        self.available_families = [f for f in pywt.families(short=True) if f not in ['bior', 'rbio', 'dmey', 'gaus', 'mexh', 'morl', 'cgau', 'shan', 'fbsp', 'cmor']]

        self.build_ui()
        self.start_audio_engine()
        self.update_ui_loop()

    # --- UI CONSTRUCTION ---
    def build_ui(self):
        # 1. Top Controls (File & Presets)
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", pady=5)
        
        tk.Label(top_frame, text="File Path:").pack(side="left")
        self.file_path_var = tk.StringVar(value="../data/Metallica_Orion.mp3")
        tk.Entry(top_frame, textvariable=self.file_path_var, width=50).pack(side="left", padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_file).pack(side="left", padx=2)
        tk.Button(top_frame, text="Load Audio", command=self.load_file, bg="lightblue").pack(side="left", padx=5)
        self.file_lbl = tk.Label(top_frame, text="No file loaded", fg="gray")
        self.file_lbl.pack(side="left", padx=10)

        # Presets
        tk.Label(top_frame, text=" | Preset:").pack(side="left")
        self.preset_var = tk.StringVar(value="my_preset.json")
        tk.Entry(top_frame, textvariable=self.preset_var, width=20).pack(side="left", padx=5)
        tk.Button(top_frame, text="Save", command=self.save_preset, bg="#90ee90").pack(side="left", padx=2)
        tk.Button(top_frame, text="Load", command=self.load_preset, bg="#ffebcd").pack(side="left", padx=2)
        
        # 2. Algo & Mix Controls
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(fill="x", pady=5)
        
        tk.Label(mid_frame, text="Method:").pack(side="left")
        ttk.Combobox(mid_frame, textvariable=self.process_method, values=['Wavelet', 'FFT', 'MDCT'], width=10, state="readonly").pack(side="left", padx=5)
        
        tk.Label(mid_frame, text="Family:").pack(side="left")
        self.fam_var = tk.StringVar(value=DEFAULT_WAV_FAMILY)
        self.fam_combo = ttk.Combobox(mid_frame, textvariable=self.fam_var, values=self.available_families, width=5, state="readonly")
        self.fam_combo.pack(side="left", padx=5)
        self.fam_combo.bind("<<ComboboxSelected>>", self.update_wav_filters)
        
        tk.Label(mid_frame, text="Filter:").pack(side="left")
        self.filt_var = tk.StringVar(value=DEFAULT_WAV_FILTER)
        self.filt_combo = ttk.Combobox(mid_frame, textvariable=self.filt_var, values=pywt.wavelist(DEFAULT_WAV_FAMILY), width=8, state="readonly")
        self.filt_combo.pack(side="left", padx=5)
        self.filt_combo.bind("<<ComboboxSelected>>", self.update_current_wavelet)

        # Mix Sliders
        tk.Label(mid_frame, text=" | Mix:").pack(side="left", padx=(10,0))
        self.mix_noise_var = tk.DoubleVar(value=self.mix_noise)
        self.mix_tone_var = tk.DoubleVar(value=self.mix_tone)
        self.mix_file_var = tk.DoubleVar(value=self.mix_file)
        
        self.create_horiz_slider(mid_frame, "Noise", self.mix_noise_var, self.update_mix)
        self.create_horiz_slider(mid_frame, "Tone", self.mix_tone_var, self.update_mix)
        self.create_horiz_slider(mid_frame, "File", self.mix_file_var, self.update_mix)

        # Master Volume
        tk.Label(mid_frame, text=" | Master Vol:").pack(side="left", padx=(10,0))
        self.master_vol_var = tk.DoubleVar(value=self.global_volume)
        self.create_horiz_slider(mid_frame, "", self.master_vol_var, self.update_master_vol)
        
        # Master Meter
        self.master_meter_canvas = tk.Canvas(mid_frame, width=150, height=20, bg="#222", highlightthickness=0)
        self.master_meter_canvas.pack(side="left", padx=10)

        # 3. Utilities Frame
        util_frame = tk.Frame(self.root)
        util_frame.pack(fill="x", pady=5)
        tk.Button(util_frame, text="Toggle Passthrough", command=self.toggle_passthrough).pack(side="left", padx=5)
        tk.Button(util_frame, text="Reset ToH", command=self.reset_toh).pack(side="left", padx=5)
        tk.Button(util_frame, text="Max All", command=lambda: self.set_all_gains(MAX_SLIDER_GAIN)).pack(side="left", padx=5)
        tk.Button(util_frame, text="Min All", command=lambda: self.set_all_gains(0.0)).pack(side="left", padx=5)

        # 4. EQ Bands
        eq_outer_frame = tk.Frame(self.root)
        eq_outer_frame.pack(fill="both", expand=True, pady=10)
        
        # Canvas + Scrollbar for horizontal scrolling if window is too small
        self.eq_canvas = tk.Canvas(eq_outer_frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(eq_outer_frame, orient="horizontal", command=self.eq_canvas.xview)
        self.eq_frame = tk.Frame(self.eq_canvas)

        self.eq_canvas.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side="bottom", fill="x")
        self.eq_canvas.pack(side="top", fill="both", expand=True)
        self.eq_canvas.create_window((0, 0), window=self.eq_frame, anchor="nw", tags="self.eq_frame")
        self.eq_frame.bind("<Configure>", lambda e: self.eq_canvas.configure(scrollregion=self.eq_canvas.bbox("all")))

        self.sliders = []
        self.meters = []
        self.mute_btns = []
        self.mute_vars = []

        for i in range(NUM_BANDS):
            band_f = tk.Frame(self.eq_frame, bd=1, relief="ridge", padx=2, pady=5)
            band_f.pack(side="left", fill="y", padx=2)
            
            # Mute Button
            m_var = tk.BooleanVar(value=True)
            self.mute_vars.append(m_var)
            m_btn = tk.Checkbutton(band_f, text="M", variable=m_var, command=lambda idx=i: self.toggle_mute(idx), indicatoron=False, width=3, bg="#90ee90", selectcolor="#ffcccc")
            m_btn.pack(side="top", pady=2)
            self.mute_btns.append(m_btn)

            # Max/Min Helpers
            tk.Button(band_f, text="↑", command=lambda idx=i: self.set_single_gain(idx, MAX_SLIDER_GAIN), font=("Arial", 8), pady=0).pack(side="top")
            
            # Slider & Meter Container
            sm_frame = tk.Frame(band_f)
            sm_frame.pack(side="top", expand=True, fill="y", pady=5)
            
            slider = ttk.Scale(sm_frame, from_=MAX_SLIDER_GAIN, to=0.0, orient="vertical", value=self.gains[i], command=lambda val, idx=i: self.update_gain(idx, val), length=250)
            slider.pack(side="left", padx=2)
            self.sliders.append(slider)
            
            meter_canvas = tk.Canvas(sm_frame, width=12, height=250, bg="#222", highlightthickness=0)
            meter_canvas.pack(side="left", padx=2)
            self.meters.append(meter_canvas)
            
            tk.Button(band_f, text="↓", command=lambda idx=i: self.set_single_gain(idx, 0.0), font=("Arial", 8), pady=0).pack(side="top")
            
            # Freq Label
            f_val = end_freqs[i]
            lbl = f"{f_val/1000:.1f}k" if f_val >= 1000 else f"{int(f_val)}"
            tk.Label(band_f, text=lbl, font=("Arial", 8)).pack(side="bottom")

    def create_horiz_slider(self, parent, label, var, command):
        f = tk.Frame(parent)
        f.pack(side="left", padx=5)
        if label: tk.Label(f, text=label).pack(side="left")
        ttk.Scale(f, from_=0.0, to=1.0, variable=var, orient="horizontal", command=command, length=100).pack(side="left")

    # --- UI CALLBACKS ---
    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.ogg")])
        if path: self.file_path_var.set(path)

    def load_file(self):
        try:
            data, fs = sf.read(self.file_path_var.get())
            if data.ndim > 1: data = np.mean(data, axis=1)
            self.file_data = data.astype(np.float32)
            self.file_play_head = 0
            self.file_lbl.config(text="File Loaded!", fg="green")
        except:
            self.file_lbl.config(text="Error loading file", fg="red")

    def update_wav_filters(self, event=None):
        fam = self.fam_var.get()
        opts = pywt.wavelist(fam)
        self.filt_combo['values'] = opts
        self.filt_var.set(opts[0])
        self.update_current_wavelet()

    def update_current_wavelet(self, event=None):
        self.current_wavelet = self.filt_var.get()

    def update_mix(self, event=None):
        self.mix_noise = self.mix_noise_var.get()
        self.mix_tone = self.mix_tone_var.get()
        self.mix_file = self.mix_file_var.get()

    def update_master_vol(self, event=None):
        self.global_volume = self.master_vol_var.get()

    def update_gain(self, idx, val):
        self.gains[idx] = float(val)

    def toggle_mute(self, idx):
        self.band_active[idx] = self.mute_vars[idx].get()
        color = "#90ee90" if self.band_active[idx] else "#ffcccc"
        self.mute_btns[idx].config(bg=color)

    def toggle_passthrough(self):
        self.passthrough_mode = not self.passthrough_mode

    def reset_toh(self):
        for i in range(NUM_BANDS): self.set_single_gain(i, INITIAL_TOH_GAINS[i])

    def set_all_gains(self, val):
        for i in range(NUM_BANDS): self.set_single_gain(i, val)

    def set_single_gain(self, idx, val):
        self.gains[idx] = val
        self.sliders[idx].set(val)

    def save_preset(self):
        data = {
            'gains': [float(s.get()) for s in self.sliders],
            'band_active': [m.get() for m in self.mute_vars],
            'method': self.process_method.get(),
            'wav_fam': self.fam_var.get(),
            'wav_filt': self.filt_var.get(),
            'mix_noise': self.mix_noise_var.get(),
            'mix_tone': self.mix_tone_var.get(),
            'mix_file': self.mix_file_var.get(),
            'master_vol': self.master_vol_var.get()
        }
        try:
            with open(self.preset_var.get(), 'w') as f: json.dump(data, f, indent=4)
            messagebox.showinfo("Success", "Preset saved!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_preset(self):
        try:
            with open(self.preset_var.get(), 'r') as f: data = json.load(f)
            if 'gains' in data:
                for i, g in enumerate(data['gains']): self.set_single_gain(i, g)
            if 'band_active' in data:
                for i, act in enumerate(data['band_active']): 
                    self.mute_vars[i].set(act)
                    self.toggle_mute(i)
            if 'method' in data: self.process_method.set(data['method'])
            if 'wav_fam' in data:
                self.fam_var.set(data['wav_fam'])
                self.update_wav_filters()
            if 'wav_filt' in data:
                self.filt_var.set(data['wav_filt'])
                self.update_current_wavelet()
            
            if 'mix_noise' in data: self.mix_noise_var.set(data['mix_noise']); self.update_mix()
            if 'mix_tone' in data: self.mix_tone_var.set(data['mix_tone']); self.update_mix()
            if 'mix_file' in data: self.mix_file_var.set(data['mix_file']); self.update_mix()
            if 'master_vol' in data: self.master_vol_var.set(data['master_vol']); self.update_master_vol()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- UI UPDATE LOOP ---
    def update_ui_loop(self):
        # 1. Update Subband Meters
        raw_vals = np.copy(self.band_variances)
        for i in range(NUM_BANDS):
            target = min(max(raw_vals[i], 0.0), 1.0)
            if target > self.smoothed_vals[i]: self.smoothed_vals[i] = target
            else: self.smoothed_vals[i] *= self.DECAY_FACTOR
            self.draw_vertical_meter(self.meters[i], self.smoothed_vals[i], 250, 12, "#00ccff")
            
        # 2. Update Master Meter
        t_master = min(max(self.master_variance, 0.0), 1.0)
        if t_master > self.smoothed_master: self.smoothed_master = t_master
        else: self.smoothed_master *= self.DECAY_FACTOR
        
        m_color = "#32cd32" # Green
        if self.master_peak >= 0.99: m_color = "#ff3333" # Red
        elif self.smoothed_master > 0.8: m_color = "#ffa500" # Orange
        
        self.draw_horizontal_meter(self.master_meter_canvas, self.smoothed_master, 150, 20, m_color)
        
        # Reschedule loop (runs every 50ms / ~20 FPS)
        self.root.after(50, self.update_ui_loop)

    def draw_vertical_meter(self, canvas, val, h, w, color):
        canvas.delete("all")
        vh = int(val * h)
        canvas.create_rectangle(0, h - vh, w, h, fill=color, outline="")

    def draw_horizontal_meter(self, canvas, val, w, h, color):
        canvas.delete("all")
        vw = int(val * w)
        canvas.create_rectangle(0, 0, vw, h, fill=color, outline="")

    # --- AUDIO CALLBACK ---
    def audio_callback(self, outdata, frames, time_info, status):
        if status: print(status)
        current_vars = np.zeros(NUM_BANDS)
        
        if self.global_volume <= 0.001:
            outdata.fill(0)
            self.band_variances[:] = 0
            self.master_variance, self.master_peak = 0.0, 0.0
            return

        final_mix = np.zeros(frames)
        broadband_signal = np.zeros(frames)
        has_bb = False

        if self.mix_tone > 0.01:
            t = np.arange(frames) / SAMPLE_RATE
            tone_accum = np.zeros(frames)
            for i in range(NUM_BANDS):
                if self.band_active[i] and self.gains[i] > 0.01:
                    freq = center_freqs[i]
                    g = self.gains[i] * BASE_TONAL_VOL * self.mix_tone
                    tone_accum += g * np.sin(2 * np.pi * freq * t + self.phases[i])
                    self.phases[i] = (self.phases[i] + 2 * np.pi * freq * frames / SAMPLE_RATE) % (2 * np.pi)
            final_mix += tone_accum

        if self.mix_noise > 0.01:
            broadband_signal += np.random.uniform(-1, 1, size=frames) * BASE_NOISE_VOL * self.mix_noise
            has_bb = True

        if self.mix_file > 0.01 and self.file_data is not None:
            remain = len(self.file_data) - self.file_play_head
            if remain >= frames:
                chunk = self.file_data[self.file_play_head : self.file_play_head + frames]
                self.file_play_head += frames
            else:
                chunk = np.concatenate((self.file_data[self.file_play_head:], self.file_data[:frames - remain]))
                self.file_play_head = frames - remain
            broadband_signal += chunk * BASE_FILE_VOL * self.mix_file
            has_bb = True

        if has_bb:
            processed = np.zeros(frames)
            SUBBAND_METER_SCALE = 20.0 
            
            if self.passthrough_mode:
                processed = broadband_signal
                try:
                    spectrum = np.fft.rfft(broadband_signal)
                    bpb = len(spectrum) / NUM_BANDS
                    for i in range(NUM_BANDS):
                        s, e = int(i*bpb), int((i+1)*bpb)
                        if e > s:
                            rms = np.sqrt(np.mean(np.square(np.abs(spectrum[s:e]))))
                            current_vars[i] = (rms / (frames / 2.0)) * SUBBAND_METER_SCALE
                except: pass
                
            else:
                pmeth = self.process_method.get()
                if pmeth == 'Wavelet':
                    try:
                        wp = pywt.WaveletPacket(data=broadband_signal, wavelet=self.current_wavelet, mode='symmetric', maxlevel=WAVELET_LEVEL)
                        nodes = wp.get_level(WAVELET_LEVEL, order='freq')
                        for i in range(min(len(nodes), NUM_BANDS)):
                            g = self.gains[i] if self.band_active[i] else 0.0
                            ndata = nodes[i].data * g
                            nodes[i].data = ndata
                            if len(ndata) > 0:
                                current_vars[i] = (np.sqrt(np.mean(np.square(np.abs(ndata)))) / np.sqrt(frames / 2.0)) * SUBBAND_METER_SCALE
                        processed = wp.reconstruct(update=False)
                    except: processed = broadband_signal

                elif pmeth == 'FFT':
                    spectrum = np.fft.rfft(broadband_signal)
                    bpb = len(spectrum) / NUM_BANDS
                    mask = np.zeros(len(spectrum))
                    for i in range(NUM_BANDS):
                        s, e = int(i*bpb), int((i+1)*bpb)
                        g = self.gains[i] if self.band_active[i] else 0.0
                        mask[s:e] = g
                        if e > s: current_vars[i] = (np.sqrt(np.mean(np.square(np.abs(spectrum[s:e]*g)))) / (frames / 2.0)) * SUBBAND_METER_SCALE
                    processed = np.fft.irfft(spectrum * mask)

                elif pmeth == 'MDCT':
                    spectrum = dct(broadband_signal, type=4, norm='ortho')
                    bpb = len(spectrum) / NUM_BANDS
                    mask = np.zeros(len(spectrum))
                    for i in range(NUM_BANDS):
                        s, e = int(i*bpb), int((i+1)*bpb)
                        g = self.gains[i] if self.band_active[i] else 0.0
                        mask[s:e] = g
                        if e > s: current_vars[i] = (np.sqrt(np.mean(np.square(np.abs(spectrum[s:e]*g)))) / np.sqrt(frames / 2.0)) * SUBBAND_METER_SCALE
                    processed = idct(spectrum * mask, type=4, norm='ortho')

                if len(processed) != frames: processed = np.resize(processed, frames)
            
            final_mix += processed

        self.band_variances[:] = current_vars[:]
        out_signal = final_mix * self.global_volume
        outdata[:, 0] = out_signal
        
        self.master_variance = np.sqrt(np.mean(np.square(out_signal))) * 4.0
        self.master_peak = np.max(np.abs(out_signal))

    def start_audio_engine(self):
        try:
            self.audio_stream = sd.OutputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, channels=1, callback=self.audio_callback)
            self.audio_stream.start()
        except Exception as e:
            messagebox.showerror("Audio Error", f"Failed to start audio stream:\n{str(e)}")

    def on_close(self):
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioEQApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
