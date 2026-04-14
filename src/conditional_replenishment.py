#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''conditional_replenishment: MSE-based block ordering + DEFLATE compression.

Controls bit-rate by selecting WHICH blocks to send each frame, based on
their MSE vs what was last sent to the receiver (sent_frame). Blocks are
sorted by MSE (highest first) and only the top --blocks_per_frame are
transmitted.

This is an independent branch from DEFLATE_video_conservative:
- DEFLATE_video_conservative: controls BR via adaptive QSS (sends all blocks)
- conditional_replenishment: controls BR via block selection (QSS is fixed)

Inherits from DEFLATE_video.py (pixel quantization + DEFLATE with fixed QSS).

Features:
    - I-frames: periodic forced full-frame refresh (--intra_period)
    - Smart refresh: zone-priority weighting, center > edges (--smart_refresh)
    - NACK feedback: receiver requests stale blocks from sender (--enable_nack)

Usage:
    # Send top 150 blocks per frame (out of 300 for 320x240 @ 16x16)
    python conditional_replenishment.py --blocks_per_frame 150

    # I-frames every 30 frames + smart refresh + NACK
    python conditional_replenishment.py --blocks_per_frame 100 --intra_period 30 --smart_refresh --enable_nack

    # With custom QSS + verbose stats
    python conditional_replenishment.py --blocks_per_frame 100 --video_quantization_step_size 2 --show_stats
'''

import numpy as np
import argparse
import struct
import zlib
import math
import time

import DEFLATE_video
import minimal_video_TFG

parser = minimal_video_TFG.parser

try:
    parser.add_argument("--blocks_per_frame", type=int, default=0,
        help="Max blocks to send per frame. 0 = send all (ordered by MSE). "
             "Lower values = less bandwidth, more block skipping (default 0).")
except argparse.ArgumentError:
    pass

try:
    parser.add_argument("--intra_period", type=int, default=0,
        help="Frames between mandatory I-frames (send all blocks). "
             "0 = disabled. E.g., 30 = one I-frame per second at 30fps (default 0).")
except argparse.ArgumentError:
    pass

try:
    parser.add_argument("--smart_refresh", action="store_true", default=False,
        help="Enable zone-priority weighting: center blocks get higher MSE priority.")
except argparse.ArgumentError:
    pass

try:
    parser.add_argument("--enable_nack", action="store_true", default=False,
        help="Enable receiver NACK feedback: receiver requests stale blocks from sender.")
except argparse.ArgumentError:
    pass

try:
    parser.add_argument("--nack_age_threshold", type=int, default=10,
        help="Frames without update before a block is considered stale for NACK (default 10).")
except argparse.ArgumentError:
    pass

NACK_MARKER = 0xFFFF

args = None


class Conditional_Replenishment(DEFLATE_video.DEFLATE_Video):
    '''MSE-based block ordering + pixel quantization + DEFLATE.

    Computes per-block MSE between the current frame and sent_frame (what
    the receiver currently displays). Blocks with the highest MSE are sent
    first, up to --blocks_per_frame. Blocks that keep being skipped
    naturally accumulate MSE and eventually get sent, preventing frozen
    artifacts.
    '''

    def __init__(self):
        global args
        if args is None:
            args = minimal_video_TFG.parser.parse_args()
        minimal_video_TFG.args = args
        DEFLATE_video.args = args

        super().__init__()

        self.blocks_per_frame = getattr(args, 'blocks_per_frame', 0)
        if self.blocks_per_frame <= 0:
            self.blocks_per_frame = self.total_blocks

        # What the receiver currently displays of our video.
        # Updated after each block is sent (with dequantized version).
        self.sent_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # Statistics for monitoring block ordering performance
        self.stats_blocks_sent = 0
        self.stats_blocks_skipped = 0

        # --- I-frame support ---
        self.intra_period = getattr(args, 'intra_period', 0)
        self.frame_counter = 0

        # --- Smart refresh: zone-priority weighting ---
        self.smart_refresh = getattr(args, 'smart_refresh', False)
        if self.smart_refresh:
            self._zone_weights = self._build_zone_weights()
        else:
            self._zone_weights = [1.0] * self.total_blocks

        # --- NACK feedback ---
        self.enable_nack = getattr(args, 'enable_nack', False)
        self._nack_requested = [0] * self.total_blocks   # TTL counter (0=no request)
        self._remote_block_age = [0] * self.total_blocks
        self._nack_send_interval = 5  # Send NACK every N frames
        self._nack_age_threshold = getattr(args, 'nack_age_threshold', 10)
        self._nack_ttl = 10  # NACK requests expire after N frames

        print(f"Conditional_Replenishment: MSE ordering, "
              f"blocks_per_frame={self.blocks_per_frame}/{self.total_blocks}, "
              f"QSS={self.quantization_step_size}")

        features = []
        if self.intra_period > 0:
            features.append(f"I-frames every {self.intra_period}")
        if self.smart_refresh:
            features.append("smart_refresh")
        if self.enable_nack:
            features.append(f"NACK (age>{self._nack_age_threshold})")
        if features:
            print(f"  Features: {', '.join(features)}")

    def _build_zone_weights(self):
        '''Pre-compute per-block priority weights based on distance from center.

        Center blocks get weight ~2.0, edge blocks get weight ~0.5.
        This multiplies the MSE before sorting, so center blocks are
        prioritized when MSE values are similar.
        '''
        cx = self.width / 2.0
        cy = self.height / 2.0
        max_dist = math.sqrt(cx ** 2 + cy ** 2)
        weights = []
        for by, bx in self.block_map:
            block_cx = bx + self.block_width / 2.0
            block_cy = by + self.block_height / 2.0
            dist = math.sqrt((block_cx - cx) ** 2 + (block_cy - cy) ** 2)
            normalized = 1.0 - (dist / max_dist)  # 1.0 at center, 0.0 at corners
            weight = 0.5 + 1.5 * normalized        # Range [0.5, 2.0]
            weights.append(weight)
        return weights

    def compute_block_diffs(self, frame):
        '''Compute per-block MSE vs sent_frame with I-frame, smart refresh, and NACK.

        - I-frames: every intra_period frames, send ALL blocks unconditionally
        - Smart refresh: weight MSE by zone priority (center > edges)
        - NACK boost: blocks requested by receiver via NACK get priority boost
        
        Uses vectorized full-frame MSE computation for efficiency:
        one subtraction + square over the entire frame, then per-block mean.
        '''
        self.frame_counter += 1

        # --- I-frame: force all blocks periodically ---
        is_intra = (self.intra_period > 0 and
                    self.frame_counter % self.intra_period == 0)

        if is_intra:
            self._block_send_mask = [True] * self.total_blocks
            self.stats_blocks_sent = self.total_blocks
            self.stats_blocks_skipped = 0
            return

        # --- Vectorized MSE: compute squared diff for the whole frame once ---
        diff_sq = (frame.astype(np.float32) - self.sent_frame.astype(np.float32)) ** 2

        mse_list = []
        for i, (by, bx) in enumerate(self.block_map):
            bh = min(self.block_height, self.height - by)
            bw = min(self.block_width, self.width - bx)

            mse = np.mean(diff_sq[by:by+bh, bx:bx+bw, :])

            # Smart refresh: apply zone-based priority weight
            weighted_mse = mse * self._zone_weights[i]

            # NACK boost: if receiver requested this block, boost priority
            # TTL-based: boost decays each frame, expires after _nack_ttl frames
            if self.enable_nack and self._nack_requested[i] > 0:
                weighted_mse = max(weighted_mse, 1.0) * 3.0
                self._nack_requested[i] -= 1

            mse_list.append((weighted_mse, i))

        # Sort by weighted MSE (highest first)
        mse_list.sort(reverse=True, key=lambda x: x[0])

        # Create mask: only send top blocks_per_frame blocks
        mask = [False] * self.total_blocks
        for j, (mse_val, idx) in enumerate(mse_list):
            if j < self.blocks_per_frame and mse_val > 0:
                mask[idx] = True

        self._block_send_mask = mask
        self.stats_blocks_sent = sum(mask)
        self.stats_blocks_skipped = self.total_blocks - self.stats_blocks_sent

        # --- Send NACK feedback (as receiver) periodically ---
        if self.enable_nack and self.frame_counter % self._nack_send_interval == 0:
            self._send_nack_feedback()

    def _send_nack_feedback(self):
        '''Send NACK to remote peer requesting stale blocks.

        Tracks which blocks on remote_frame have not been updated recently.
        Sends a compact list of stale block indices to the remote peer
        so they can boost priority for those blocks.

        Packet format: [NACK_MARKER (2B)] + [block_idx_0 (2B), block_idx_1 (2B), ...]
        '''
        stale_blocks = []
        for i in range(self.total_blocks):
            self._remote_block_age[i] += self._nack_send_interval
            if self._remote_block_age[i] >= self._nack_age_threshold:
                stale_blocks.append(i)

        if not stale_blocks:
            return

        # Limit NACK size to avoid UDP fragmentation (~700 indices max)
        stale_blocks = stale_blocks[:700]

        header = struct.pack(self._header_format, NACK_MARKER)
        payload = struct.pack(f"!{len(stale_blocks)}H", *stale_blocks)
        packet = header + payload
        try:
            self.video_sock.sendto(packet, self.video_addr)
        except BlockingIOError:
            pass

    def receive_video_block(self):
        '''Receive video block or NACK feedback from the shared video socket.

        Distinguishes between:
        - NACK packets (header == NACK_MARKER): parsed as block request list
        - Video packets (header < total_blocks): decompressed and placed normally
        '''
        try:
            packet, addr = self.video_sock.recvfrom(65536)
        except BlockingIOError:
            return None, 0

        if len(packet) < self.header_size:
            return None, 0

        header = packet[:self.header_size]
        block_idx, = struct.unpack(self._header_format, header)

        # --- NACK feedback packet ---
        if block_idx == NACK_MARKER:
            if self.enable_nack:
                payload = packet[self.header_size:]
                n_indices = len(payload) // 2
                if n_indices > 0:
                    nack_indices = struct.unpack(f"!{n_indices}H", payload)
                    for idx in nack_indices:
                        if 0 <= idx < self.total_blocks:
                            self._nack_requested[idx] = self._nack_ttl
            return None, 0

        # --- Regular compressed video block ---
        if block_idx >= self.total_blocks:
            return None, 0

        compressed = packet[self.header_size:]
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

        # Reset age for received block (NACK tracking)
        if self.enable_nack:
            self._remote_block_age[block_idx] = 0

        return block_idx, len(packet)

    def send_video_block(self, block_idx, frame):
        '''Quantize + DEFLATE + send, then update sent_frame.

        After sending, updates sent_frame with the dequantized version
        of the block (reflects what the receiver actually reconstructs
        after quantization round-trip). This ensures MSE calculations
        in the next frame match the receiver's actual display buffer.
        '''
        result = super().send_video_block(block_idx, frame)

        # Update sent_frame with what the receiver now has (after Q/DQ round-trip)
        by, bx = self.block_map[block_idx]
        bh = min(self.block_height, self.height - by)
        bw = min(self.block_width, self.width - bx)
        block = frame[by:by+bh, bx:bx+bw, :]

        # Quantize-dequantize to match receiver's reality
        self.sent_frame[by:by+bh, bx:bx+bw, :] = self.dequantize(self.quantize(block))

        return result


class Conditional_Replenishment__verbose(Conditional_Replenishment, minimal_video_TFG.Minimal_Video__verbose):
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
        intercom_app = Conditional_Replenishment__verbose()
    else:
        intercom_app = Conditional_Replenishment()

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
