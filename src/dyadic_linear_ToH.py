#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""Providing linear splitting of the dyadic subbands using wavelet packets."""

import numpy as np
import pywt
import logging
import math
import sys
import os
sys.path.append('../src')
import minimal
try:
    from dyadic_ToH import Dyadic_ToH as Threshold
    from dyadic_ToH import Dyadic_ToH__verbose as Threshold__verbose
except ImportError:
    logging.warning("Dyadic_ToH not found, falling back to Stereo_MST_Coding_32 for inheritance.")
    try:
        from stereo_MST_coding_32 import Stereo_MST_Coding_32 as Threshold
        from stereo_MST_coding_32 import Stereo_MST_Coding_32__verbose as Threshold__verbose
    except ImportError:
        logging.warning("Stereo_MST_Coding_32 not found. Fallback to minimal Buffer (Critical!)")
        # Extreme fallback if even Stereo is missing, though unlikely in this project
        import buffer
        class Threshold(buffer.Buffering): pass
        class Threshold__verbose(buffer.Buffering__verbose): pass

try:
    from DEFLATE_byteplanes3 import DEFLATE_BytePlanes3 as EC
except ImportError:
    logging.warning("DEFLATE_BytePlanes3 not found, falling back to DEFLATE_raw (High Bitrate Warning!)")
    import DEFLATE_raw as EC

import argparse

# Argument Parsing (Robust)
try:
    minimal.parser.add_argument("-p", "--WPT_levels", type=int, default=2, help="Number of levels of WPT (linear subbands per dyadic one)")
except argparse.ArgumentError: pass
try:
    minimal.parser.add_argument("--advanced", action="store_true", help="Use the alternative advanced calculation for frequency processing")
except argparse.ArgumentError: pass
try:
    minimal.parser.add_argument("-q", type=float, default=0.0, help="Quantization quality parameter (Max Q)")
except argparse.ArgumentError: pass
try:
    minimal.parser.add_argument("--custom_toh", action="store_true", help="Use custom_ToH.txt for quantization steps")
except argparse.ArgumentError: pass

class Dyadic_Linear_ToH(Threshold):

    def __init__(self):
        if minimal.args.filename:
             minimal.args.filename = os.path.expanduser(minimal.args.filename)

        # --- FIX: INHERITANCE MISMATCH ---
        #target_subbands = getattr(minimal.args, 'WPT_levels', 4)
        #self.WPT_levels = int(np.log2(target_subbands))
        self.WPT_levels = minimal.args.WPT_levels
        if self.WPT_levels < 1: self.WPT_levels = 1 # NOOOOOOOOOOOOO
        minimal.args.levels = str(self.WPT_levels)

        super().__init__()
        logging.info(__doc__)

        self.wavelet = pywt.Wavelet(minimal.args.wavelet_name)
        self.wpt_levels = 0

        # --- Q Parameter Fix ---
        self.max_q = getattr(minimal.args, 'q', 0.0)
        if self.max_q == 0.0:
             val = getattr(minimal.args, 'minimal_quantization_step_size', 16.0)
             self.max_q = float(val)

        # --- Overlap & Levels ---
        self.max_filters_length = max(self.wavelet.dec_len, self.wavelet.rec_len)
        # (Levels calculated before super init)

        self.number_of_overlapped_samples = self.max_filters_length * (1 << self.WPT_levels)
        self.overlap = self.number_of_overlapped_samples

        logging.info(f"WPT levels = {self.WPT_levels} ({2**self.WPT_levels} subbands)")

        # --- Buffers (Stereo enforced) ---
        self.num_channels = minimal.args.number_of_channels
        fpc = minimal.args.frames_per_chunk
        buffer_channels = 2 if self.num_channels == 1 else self.num_channels

        self.e_chunk_list = [np.zeros((fpc, buffer_channels), dtype=np.int32) for _ in range(3)]
        self.d_chunk_list = [np.zeros((fpc, buffer_channels), dtype=np.int32) for _ in range(3)]

        # --- Quantization Steps ---
        if getattr(minimal.args, 'custom_toh', False) and os.path.exists('custom_ToH.txt'):
            try:
                with open('custom_ToH.txt', 'r') as f:
                     self.quantization_steps = [float(x) for x in f.read().split()]
            except: self.quantization_steps = self.calculate_linear_quantization_steps(self.max_q)
        else:
            self.quantization_steps = self.calculate_linear_quantization_steps(self.max_q)

        logging.info(f"quantization steps = {self.quantization_steps}")
        try: del self.unpack
        except: pass

    def calculate_linear_quantization_steps(self, max_q):
         # plot 16.97 * (log10(x) ** 2) - 106.98 * log10(x) + 173.82 + 10 ** -3 * (x / 1000) ** 4, 3.64 * (x / 1000) ** -0.8 - 6.5 * exp((-0.6) * (x / 1000 - 3.3) ** 2) + 10 ** -3 * (x / 1000) ** 4
        def calc_advanced(f):
            return 16.97 * (np.log10(f) ** 2) - 106.98 * np.log10(f) + 173.82 + 10 ** -3 * (f / 1000) ** 4
        def calc_advanced(f):
            return 1
        def calc_standard(f):
            return 3.64 * (f / 1000) ** -0.8 - 6.5 * math.exp((-0.6) * (f / 1000 - 3.3) ** 2) + 10 ** -3 * (f / 1000) ** 4

        calc = calc_advanced if getattr(minimal.args, 'advanced', False) else calc_standard
        f = 22050
        average_SPLs = []
        num_bands = 2**self.WPT_levels
        band_width = f / num_bands

        for i in range(num_bands):
             start_f = i * band_width
             if start_f == 0: start_f = 1
             end_f = (i+1) * band_width
             steps_f = np.linspace(start_f, end_f, 10)
             avg = np.mean([calc(val) for val in steps_f])
             average_SPLs.append(avg)

        min_SPL = np.min(average_SPLs)
        max_SPL = np.max(average_SPLs)

        # FIX: Dynamic min_step to allow compression (Bitrate Control)
        # Professor request: ~250kbps.
        # If max_q is high (e.g. 64), min_step should also increase slightly to allow compression in sensitive bands,
        # but much less than non-sensitive bands.

        # Heuristic: min_step is 1 (lossless) only if max_q is small (< 8).
        # If max_q > 8, min_step scales logarithmically/linearly.

        if max_q <= 1.0:
            min_step = 1
        else:
            # Tuned factor: ULTRA Aggressive scaling for compression (~250kbps target).
            # We need effective bit depth ~4 bits. Max Step ~4096.
            # We set min_step to be close to max_q to force global bit reduction.
            min_step = max(1, max_q * 0.75)

        qs = []
        for s in average_SPLs:
            # Linear mapping with dynamic min_step
            step = round((s - min_SPL) / (max_SPL - min_SPL + 1e-6) * (max_q - min_step) + min_step)
            if step < 1: step = 1
            qs.append(step)
        print("--------------->", qs)
        return qs

    def analyze(self, chunk):
        #if chunk.shape[1] == 1: chunk = np.column_stack((chunk, chunk))
        self.e_chunk_list.pop(0)
        self.e_chunk_list.append(chunk)
        o = self.overlap; fpc = minimal.args.frames_per_chunk
        extended_chunk = np.concatenate([self.e_chunk_list[0][-o:], self.e_chunk_list[1], self.e_chunk_list[2][:o]])
        packet_data_flat = np.empty((fpc, chunk.shape[1]), dtype=np.int32)

        for c in range(chunk.shape[1]):
            wp = pywt.WaveletPacket(data=extended_chunk[:, c], wavelet=self.wavelet, mode='per', maxlevel=self.WPT_levels)
            nodes = wp.get_level(self.WPT_levels, 'freq')
            col_data = []
            for i, node in enumerate(nodes):
                data = node.data
                q = self.quantization_steps[i] if i < len(self.quantization_steps) else 1
                data = data / q
                offset = o // (2**self.WPT_levels)
                sliced = data[offset:-offset] if offset > 0 else data
                col_data.append(sliced)
            c_col = np.concatenate(col_data)
            #if len(c_col) != fpc:
            #    c_col = c_col[:fpc] if len(c_col) > fpc else np.pad(c_col, (0, fpc - len(c_col)))
            packet_data_flat[:, c] = np.rint(c_col)

        return packet_data_flat.astype(np.int32)

    def synthesize(self, chunk_WP):
        self.d_chunk_list.pop(0)
        self.d_chunk_list.append(chunk_WP)
        o = self.overlap; fpc = minimal.args.frames_per_chunk
        num_bands = 2**self.WPT_levels
        band_len = fpc // num_bands
        offset = o // num_bands
        reconstructed_chunk = np.empty((fpc, chunk_WP.shape[1]), dtype=np.float32)

        for c in range(chunk_WP.shape[1]):
            coeffs = []
            prev, curr, next = [x[:, c] for x in self.d_chunk_list]
            for b in range(num_bands):
                s_start, s_end = b*band_len, (b+1)*band_len
                p_tail = prev[s_start:s_end][-offset:] if offset > 0 else []
                n_head = next[s_start:s_end][:offset] if offset > 0 else []
                ext_band = np.concatenate([p_tail, curr[s_start:s_end], n_head])
                q = self.quantization_steps[b] if b < len(self.quantization_steps) else 1
                coeffs.append(ext_band * q)

            dummy_len = fpc + 2*o
            wp = pywt.WaveletPacket(data=np.zeros(dummy_len), wavelet=self.wavelet, mode='per', maxlevel=self.WPT_levels)
            nodes = wp.get_level(self.WPT_levels, 'freq')
            for i, node in enumerate(nodes):
                if True:#if i < len(coeffs):
                     tgt = len(node.data); src = coeffs[i]
                     node.data = src[:tgt] if len(src) >= tgt else np.pad(src, (0, tgt - len(src)))
            rec = wp.reconstruct(update=False)
            rec_final = rec[o:-o] if o > 0 else rec
            reconstructed_chunk[:, c] = rec_final[:fpc]

        #if minimal.args.number_of_channels == 1 and chunk_WP.shape[1] == 2:
        #     return np.clip(reconstructed_chunk[:, 0].reshape(-1, 1), -32768, 32767)
        return np.clip(reconstructed_chunk, -32768, 32767)

    def pack(self, chunk_number, chunk):
        analyzed_chunk = self.analyze(chunk)
        packed_chunk = EC.pack(self, chunk_number, analyzed_chunk)
        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, analyzed_chunk = EC.unpack(self, packed_chunk)
        try: chunk = self.synthesize(analyzed_chunk)
        except: chunk = np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels))
        return chunk_number, chunk

# FIXED INHERITANCE ORDER: Mixin (Threshold__verbose) must be first to capture stats
class Dyadic_Linear_ToH__verbose(Threshold__verbose, Dyadic_Linear_ToH): pass

try: import argcomplete
except: argcomplete = lambda *args, **kwargs: None

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try: argcomplete.autocomplete(minimal.parser)
    except: pass
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Dyadic_Linear_ToH__verbose()
    else: intercom = Dyadic_Linear_ToH()
    try: intercom.run()
    except KeyboardInterrupt: minimal.parser.exit("\nInterrupted by user")
    finally: intercom.print_final_averages()

