#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''DEFLATE_video: Dead-zone quantization of pixel values + DEFLATE compression.

This module provides simple block-wise pixel quantization without adaptive
bandwidth control. The quantization step size (QSS) remains constant
during execution.

For adaptive quantization based on packet loss, use DEFLATE_video_conservative.py.
For DCT-based compression, use DEFLATE_video_DCT.py.

Usage:
    # Pixel quantization, QSS=2 (fixed)
    python DEFLATE_video.py --video_quantization_step_size 2

    # Verbose mode with statistics
    python DEFLATE_video.py --video_quantization_step_size 3 --show_stats
'''

import zlib
import numpy as np
import struct
import time
import argparse

import minimal_video_TFG

parser = minimal_video_TFG.parser

try:
    parser.add_argument("--video_quantization_step_size", type=int, default=2,
        help="Quantization step size for video blocks (default 2). "
             "Higher values = more compression, less quality.")
except argparse.ArgumentError:
    pass  # Already added by another module

args = None


class DEFLATE_Video(minimal_video_TFG.Minimal_Video):
    '''Dead-zone quantization of pixel values + DEFLATE (fixed QSS).
    
    Pipeline: block → quantize (÷QSS) → zlib compress → send
              receive → zlib decompress → dequantize (×QSS) → place
    '''

    def __init__(self):
        global args
        if args is None:
            args = minimal_video_TFG.parser.parse_args()
        minimal_video_TFG.args = args

        super().__init__()

        self.quantization_step_size = max(1, getattr(args, 'video_quantization_step_size', 2))
        print(f"DEFLATE_Video: pixel quantization, QSS={self.quantization_step_size}")

    def quantize(self, block):
        '''Dead-zone quantizer for pixel values (uint8 → uint8).'''
        if self.quantization_step_size <= 1:
            return block
        return (block // self.quantization_step_size).astype(np.uint8)

    def dequantize(self, quantized_block):
        '''Inverse dead-zone quantizer (uint8 → uint8).'''
        if self.quantization_step_size <= 1:
            return quantized_block
        return (quantized_block * self.quantization_step_size).astype(np.uint8)

    def send_video_block(self, block_idx, frame):
        '''Quantize + DEFLATE + send.
        
        Properly handles edge blocks that may be smaller than block_height x block_width.
        '''
        by, bx = self.block_map[block_idx]
        bh = min(self.block_height, self.height - by)
        bw = min(self.block_width, self.width - bx)
        block = frame[by:by+bh, bx:bx+bw, :]
        quantized = self.quantize(block)
        compressed = zlib.compress(quantized.tobytes())
        header = struct.pack(self._header_format, block_idx)
        packet = header + compressed
        try:
            self.video_sock.sendto(packet, self.video_addr)
        except BlockingIOError:
            pass
        return len(packet)

    def receive_video_block(self):
        '''Receive + decompress + dequantize.'''
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
        by, bx = self.block_map[block_idx]
        bh = min(self.block_height, self.height - by)
        bw = min(self.block_width, self.width - bx)
        quantized = np.frombuffer(decompressed, dtype=np.uint8).reshape(bh, bw, 3)
        block = self.dequantize(quantized)
        self.remote_frame[by:by+bh, bx:bx+bw, :] = block
        return block_idx, len(packet)


class DEFLATE_Video__verbose(DEFLATE_Video, minimal_video_TFG.Minimal_Video__verbose):
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
        intercom_app = DEFLATE_Video__verbose()
    else:
        intercom_app = DEFLATE_Video()

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

