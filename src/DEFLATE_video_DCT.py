#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''DEFLATE_video_DCT: 2D-DCT + DEFLATE compression with fixed QSS.

This module applies a separable 2D Discrete Cosine Transform (DCT) to each
video block, concentrating energy in low-frequency coefficients. Dead-zone
quantization is then applied to DCT coefficients, removing mostly high-frequency
detail (less visible to the eye), yielding better compression at similar
visual quality compared to direct pixel quantization.

Pipeline: block → pad to full size → 2D DCT → quantize (÷QSS) → DEFLATE → send
          receive → DEFLATE decompress → dequantize (×QSS) → 2D IDCT → crop → place

Usage:
    # DCT with QSS=4 (fixed)
    python DEFLATE_video_DCT.py --video_quantization_step_size 4

    # DCT with higher initial QSS (more compression, less quality)
    python DEFLATE_video_DCT.py --video_quantization_step_size 8 --show_stats
'''

import zlib
import numpy as np
import struct
import time
import argparse
import scipy.fftpack

import minimal_video_TFG

parser = minimal_video_TFG.parser

try:
    parser.add_argument("--video_quantization_step_size", type=int, default=4,
        help="Quantization step size for DCT coefficients (default 4). "
             "Higher values = more compression, less quality.")
except argparse.ArgumentError:
    pass  # Already added by another module

args = None


class DEFLATE_Video_DCT(minimal_video_TFG.Minimal_Video):
    '''2D-DCT + dead-zone quantization of coefficients + DEFLATE.

    Each block is padded to (block_height × block_width), transformed
    with a separable 2D DCT, quantized (float→int16), compressed with
    DEFLATE, and transmitted. The receiver decompresses, dequantizes,
    applies the inverse DCT, clips to [0,255] and crops to the actual
    block size.
    
    DCT-based compression is particularly effective for natural images
    because energy is concentrated in low-frequency coefficients; high-
    frequency quantization noise is typically less perceptible.
    '''

    def __init__(self):
        global args
        if args is None:
            args = minimal_video_TFG.parser.parse_args()
        minimal_video_TFG.args = args

        super().__init__()

        self.quantization_step_size = max(1, getattr(args, 'video_quantization_step_size', 4))
        print(f"DEFLATE_Video_DCT: 2D-DCT compression, QSS={self.quantization_step_size}")

    def quantize(self, dct_block):
        '''Dead-zone quantizer for DCT coefficients (float32 → int16).'''
        if self.quantization_step_size <= 1:
            return dct_block.astype(np.int16)
        return (dct_block / self.quantization_step_size).astype(np.int16)

    def dequantize(self, quantized_block):
        '''Inverse quantizer (int16 → float32).'''
        if self.quantization_step_size <= 1:
            return quantized_block.astype(np.float32)
        return quantized_block.astype(np.float32) * self.quantization_step_size

    def send_video_block(self, block_idx, frame):
        '''DCT + quantize + DEFLATE + send.'''
        by, bx = self.block_map[block_idx]
        bh = min(self.block_height, self.height - by)
        bw = min(self.block_width, self.width - bx)
        block = frame[by:by+bh, bx:bx+bw, :]

        # Pad to full block size so the DCT operates on a fixed grid
        padded = np.zeros((self.block_height, self.block_width, 3), dtype=np.float32)
        padded[:bh, :bw, :] = block.astype(np.float32)

        # Separable 2D DCT per channel
        dct_block = np.empty_like(padded)
        for c in range(3):
            dct_block[:, :, c] = scipy.fftpack.dct(
                scipy.fftpack.dct(padded[:, :, c], axis=0, norm='ortho'),
                axis=1, norm='ortho')

        quantized = self.quantize(dct_block)
        compressed = zlib.compress(quantized.tobytes())
        header = struct.pack(self._header_format, block_idx)
        packet = header + compressed
        try:
            self.video_sock.sendto(packet, self.video_addr)
        except BlockingIOError:
            pass
        return len(packet)

    def receive_video_block(self):
        '''Receive + decompress + dequantize + inverse DCT.'''
        try:
            packet, addr = self.video_sock.recvfrom(65536)
        except BlockingIOError:
            return None, 0
        header = packet[:self.header_size]
        compressed = packet[self.header_size:]
        block_idx, = struct.unpack(self._header_format, header)
        try:
            decompressed = zlib.decompress(compressed)
        except zlib.error:
            return None, 0

        quantized = np.frombuffer(decompressed, dtype=np.int16).reshape(
            self.block_height, self.block_width, 3)
        dct_block = self.dequantize(quantized)

        block = np.empty_like(dct_block)
        for c in range(3):
            block[:, :, c] = scipy.fftpack.idct(
                scipy.fftpack.idct(dct_block[:, :, c], axis=1, norm='ortho'),
                axis=0, norm='ortho')
        block = np.clip(block, 0, 255).astype(np.uint8)

        by, bx = self.block_map[block_idx]
        bh = min(self.block_height, self.height - by)
        bw = min(self.block_width, self.width - bx)
        self.remote_frame[by:by+bh, bx:bx+bw, :] = block[:bh, :bw, :]
        return block_idx, len(packet)


class DEFLATE_Video_DCT__verbose(DEFLATE_Video_DCT, minimal_video_TFG.Minimal_Video__verbose):
    '''Verbose version with statistics.'''
    pass


if __name__ == "__main__":
    try:
        import argcomplete
        argcomplete.autocomplete(minimal_video_TFG.parser)
    except Exception:
        pass

    args = minimal_video_TFG.parser.parse_args()
    if not hasattr(args, 'destination_address') or not args.destination_address:
        args.destination_address = "localhost"

    verbose_enabled = (getattr(args, 'show_stats', False) or
                       getattr(args, 'show_samples', False) or
                       getattr(args, 'show_spectrum', False))

    if verbose_enabled:
        intercom_app = DEFLATE_Video_DCT__verbose()
    else:
        intercom_app = DEFLATE_Video_DCT()

    try:
        intercom_app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(intercom_app, 'print_final_averages') and callable(intercom_app.print_final_averages):
            time.sleep(0.2)
            intercom_app.print_final_averages()
        print("Program terminated.")
