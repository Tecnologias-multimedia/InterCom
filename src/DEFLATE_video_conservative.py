#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''DEFLATE_video_conservative: Pixel quantization + DEFLATE with adaptive QSS.

This module applies the same conservative bandwidth control strategy used in
BR_control_conservative: when packets are lost, QSS is doubled; otherwise it
gradually reduces by dividing by 1.1 every control period (1 second).

This aggressive adaptation helps maintain video quality within available bandwidth.

Usage:
    python DEFLATE_video_conservative.py --video_quantization_step_size 2 --show_stats
'''

import zlib
import numpy as np
import struct
import threading
import time
import argparse

import minimal_video_TFG

parser = minimal_video_TFG.parser

try:
    parser.add_argument("--video_quantization_step_size", type=int, default=2,
        help="Quantization step size for video blocks (default 2). "
             "Serves as minimum; adapted dynamically based on packet loss.")
except argparse.ArgumentError:
    pass  # Already added by another module

args = None


class DEFLATE_Video_Conservative(minimal_video_TFG.Minimal_Video):
    '''Dead-zone quantization of pixel values + DEFLATE with adaptive QSS.
    
    Same as DEFLATE_Video but adds a control thread that monitors packet
    loss and adjusts QSS:
    - If loss > 2 blocks: QSS *= 2 (increase quantization)
    - Otherwise: QSS /= 1.1 (gradually improve quality)
    
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
        self.minimal_quantization_step_size = self.quantization_step_size

        # Counters for adaptive QSS control
        self.number_of_sent_blocks = 0
        self.number_of_received_blocks = 0

        # Start conservative adaptive QSS thread
        control_thread = threading.Thread(target=self.data_flow_control, daemon=True)
        control_thread.start()

        print(f"DEFLATE_Video_Conservative: pixel quantization with adaptive QSS, "
              f"base QSS={self.quantization_step_size}")

    def data_flow_control(self):
        '''Conservative adaptive QSS based on block loss ratio.
        
        Monitors the ratio of lost blocks vs sent blocks. Uses a proportional
        threshold (5% loss) instead of an absolute count, which avoids false
        positives caused by the timing gap between send/receive threads.
        '''
        while self.running:
            sent = self.number_of_sent_blocks
            received = self.number_of_received_blocks
            number_of_lost = sent - received
            # Use proportional threshold: only react if >5% of blocks were lost
            if sent > 0 and (number_of_lost / sent) > 0.05:
                self.quantization_step_size = int(self.quantization_step_size * 1.3) + 1
            self.quantization_step_size = int(self.quantization_step_size / 1.1)
            if self.quantization_step_size < self.minimal_quantization_step_size:
                self.quantization_step_size = self.minimal_quantization_step_size
            self.number_of_sent_blocks = 0
            self.number_of_received_blocks = 0
            time.sleep(1.0)

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
        self.number_of_sent_blocks += 1
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
        self.number_of_received_blocks += 1
        return block_idx, len(packet)


class DEFLATE_Video_Conservative__verbose(DEFLATE_Video_Conservative, minimal_video_TFG.Minimal_Video__verbose):
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
        intercom_app = DEFLATE_Video_Conservative__verbose()
    else:
        intercom_app = DEFLATE_Video_Conservative()

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
