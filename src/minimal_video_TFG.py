#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""
Minimal_Video: Extends minimal.py to add video transmission/display without compression/encoding, using raw data. Includes verbose option (--show_stats, --show_samples and --show_spectrum).

    - Full‐duplex video is transmitted via UDP without using queues: the frame is sent directly.
    - The --show_video flag enables video display and transmission. By default, it is disabled.
    - Without --show_video, it behaves exactly like minimal.py (audio only).

A UDP socket is used for transmission, and frames are fragmented.
Header (big-endian): FragIdx(H) – Only the fragment position is transmitted.

New parameters:
    --video_payload_size : Desired size (bytes) of video/UDP fragment payload (default 1400).
    --width : Video width (default 320).
    --height : Video height (default 240).
    --fps : Video frames per second (default 30).
    --listening_video_port : Port to listen for video (default 4445).
    --destination_video_port : Port to send video to (default 4445).
    --camera_index : Index of the camera to use (default 0).
"""

# Originally implemented by JORGE JESUS SANCHEZ RIVAS.

import cv2
import socket
import struct
import threading
import time
import math
import numpy as np
import select
import argparse
import psutil
import logging
import minimal

spinner = minimal.spinning_cursor()

def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text

if not hasattr(minimal, 'parser'):
    minimal.parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser = minimal.parser

parser.add_argument("--block_size", type=int, default=16, help="Block size for square video blocks (default 16)")
parser.add_argument("-v", "--video_payload_size", type=int, default=1400, help="Desired size (bytes) of video payload/UDP fragment (default 1400).")

# In Linux: v4l2-ctl -d /dev/video0 --list-formats-ext
parser.add_argument("-w", "--width", type=int, default=320, help="Video width (default 320)")
parser.add_argument("-g", "--height", type=int, default=240, help="Video height (default 240)")
parser.add_argument("-z", "--fps", type=int, default=30, help="Video frames per second (default 30)")

parser.add_argument("-lvp", "--listening_video_port", type=int, default=4445, help="Port to listen on for receiving video (default 4445).")
parser.add_argument("-dvp", "--destination_video_port", type=int, default=4445, help="Port to send video to (default 4445).")
parser.add_argument("--camera_index", type=int, default=0, help="Index of the camera to use (default 0).")

 
args = None

class Minimal_Video(minimal.Minimal):
    def __init__(self):
        global args
        if args is None:
            args = minimal.parser.parse_args()
        minimal.args = args

        super().__init__()

        #if not args.show_video:
        #    return

        self.video_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.video_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8388608)
        self.video_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8388608)
        self.video_sock.setblocking(False)
        try:
            self.video_sock.bind(("0.0.0.0", args.listening_video_port))
        except OSError as e:
            print(f"Error binding video socket: {e}")
            raise
        self.video_addr = (args.destination_address, args.destination_video_port)

        self._header_format = "!H"
        self.header_size = 2
        self.effective_video_payload_size = args.video_payload_size
        self.max_payload_possible = self.effective_video_payload_size - self.header_size
        self.effective_video_payload_size = max(1, min(args.video_payload_size, self.max_payload_possible))
        if self.effective_video_payload_size != args.video_payload_size:
            print(f"Warning: --video_payload_size adjusted to {self.effective_video_payload_size} bytes.")

        self.block_width = self.block_height = getattr(args, 'block_size', 8)

        self.cap = None
        self.width = 0
        self.height = 0
        self.fps = 0

        self.expected_frame_size = 0
        self.block_map = []  # Lista de (y, x) para cada bloque
        self.total_blocks = 0

        try:
            self.cap = cv2.VideoCapture(args.camera_index)
            if not self.cap.isOpened():
                raise IOError(f"Could not open camera with index {args.camera_index}.")
            if args.width > 0:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
            if args.height > 0:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
            if args.fps > 0:
                self.cap.set(cv2.CAP_PROP_FPS, args.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))

            self.expected_frame_size = self.width * self.height * 3

            # Crear mapa de bloques (y, x)
            self.block_map = []
            for by in range(0, self.height, self.block_height):
                for bx in range(0, self.width, self.block_width):
                    self.block_map.append((by, bx))
            self.total_blocks = len(self.block_map)

            self.remote_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        except Exception as e:
            print(f"Error initializing camera: {e}. Disabling video.")
            if self.cap:  
                self.cap.release()
            self.cap = None

        self.running = True

    def capture_image(self):
        _, frame = self.cap.read()
        return frame.tobytes()


    def send_video_block(self, block_idx, frame):
        by, bx = self.block_map[block_idx]
        block = frame[by:by+self.block_height, bx:bx+self.block_width, :]
        payload = block.tobytes()
        header = struct.pack(self._header_format, block_idx)
        packet = header + payload
        try:
            self.video_sock.sendto(packet, self.video_addr)
        except BlockingIOError:
            print(f"Socket blocked while sending block {block_idx}.")
            pass
        return len(packet)

    def receive_video_block(self):
        rlist, _, _ = select.select([self.video_sock], [], [], 0.001)
        if rlist:
            # El tamaño máximo de bloque es block_width*block_height*3
            max_block_bytes = self.block_width * self.block_height * 3
            packet, addr = self.video_sock.recvfrom(self.header_size + max_block_bytes)
            header = packet[:self.header_size]
            payload = packet[self.header_size:]
            block_idx, = struct.unpack(self._header_format, header)
            by, bx = self.block_map[block_idx]
            block_shape = (min(self.block_height, self.height - by), min(self.block_width, self.width - bx), 3)
            block = np.frombuffer(payload, dtype=np.uint8).reshape(block_shape)
            self.remote_frame[by:by+block_shape[0], bx:bx+block_shape[1], :] = block
            return block_idx, len(packet)
        return None, 0

    def show_video(self):
        cv2.imshow(f"Video (Cam {args.camera_index})", self.remote_frame) # Título de ventana modificado
        cv2.waitKey(1)

    def video_loop(self):
        try:
            while self.running:
                _, frame = self.cap.read()
                for block_idx in range(self.total_blocks):
                    self.send_video_block(block_idx, frame)
                    self.receive_video_block()
                self.show_video()
        except Exception as e:
            print(f"Error in video loop: {e}")
            pass

    def run(self):
        #if not args.show_video or self.cap is None:
        #    print("Video disabled. Running audio-only mode.")
        #    super().run()
        #    return

        print("Starting video with unified loop and simplified protocol...")

        t_unified = threading.Thread(target=self.video_loop, daemon=True, name="UnifiedVideoThread")
        t_unified.start()

        try:
            super().run()
        except KeyboardInterrupt:
            print("Keyboard interrupt detected.")
        finally:
            self.running = False
            if t_unified.is_alive():
                t_unified.join(timeout=1)
            if hasattr(self, 'cap') and self.cap.isOpened():
                self.cap.release()
            cv2.destroyAllWindows()
            if hasattr(self, 'video_sock') and self.video_sock:
                self.video_sock.close()
            print("Video application stopped.")

class Minimal_Video__verbose(Minimal_Video, minimal.Minimal__verbose):
    def __init__(self):
        # Initialize base class first (Minimal_Video, which extends Minimal)
        super().__init__()

        # Define video metrics BEFORE initializing verbose parent
        self.video_sent_bytes_count = 0
        self.video_sent_messages_count = 0
        self.video_received_bytes_count = 0
        self.video_received_messages_count = 0

        # Define audio metrics that verbose class expects
        self.sent_bytes_count = 0
        self.received_bytes_count = 0
        self.sent_messages_count = 0
        self.received_messages_count = 0

        # Initialize verbose parent (Minimal__verbose)
        try:
            minimal.Minimal__verbose.__init__(self)
            print(f"Verbose Mode: stats cycle = {self.seconds_per_cycle}s")
        except AttributeError as e:
            print(f"Error: Could not initialize minimal.Minimal__verbose: {e}")            

        self._total_audio_sent_bytes = 0
        self._total_audio_received_bytes = 0
        self._total_video_sent_bytes = 0
        self._total_video_received_bytes = 0
        self._stats_start_time = time.time()

        self._fragments_received_this_cycle = 0
        self._fragments_received_history = []

        self.total_number_of_sent_frames = 0
        self.frame_time = 1.0 / self.fps

        # Video quality metrics (MSE/PSNR)
        self.last_sent_frame = None
        self.last_received_frame = None
        self.accumulated_mse = 0.0
        self.accumulated_psnr = 0.0
        self.frames_analyzed = 0
        self.last_mse = 0.0
        self.last_psnr = 0.0

        self.end_time = None
        if hasattr(args, "reading_time") and args.reading_time:
            self.end_time = time.time() + float(args.reading_time)
            print(f"Program will terminate automatically after {args.reading_time} seconds")
            print(f"Scheduled end time: {time.strftime('%H:%M:%S', time.localtime(self.end_time))}")
            self.time_event = threading.Event()

    def print_header(self):
        header1 = (
            f"{'':8s}"
            " | " + f"{'AUDIO (msg)':^13s}"
            " | " + f"{'VIDEO (msg)':^13s}"
            " | " + f"{'AUDIO (kbps)':^15s}"
            " | " + f"{'VIDEO (kbps)':^15s}"
            " | " + f"{'VIDEO METRICS':^20s}"
            " |     " + f"{'CPU (%)':^8s}"
        )
        header2 = (
            f"{'Cycle':>8s}"
            " | " + f"{'Sent':>5s} {'Recv':>5s}"
            "   | " + f"{'Sent':>5s} {'Recv':>5s}"
            "   | " + f"{'Sent':>6s} {'Recv':>6s}"
            "   | " + f"{'Sent':>6s} {'Recv':>6s}"
            "   | " + f"{'MSE':>9s} {'PSNR(dB)':>9s}"
            "   | " + f"{'Program':>4s} {'System':>4s}"
        )
        print(header1)
        print(header2)
        print("=" * (8 + 3 + 13 + 3 + 13 + 3 + 15 + 3 + 15 + 3 + 20 + 3 + 8 + 9))

    def print_footer(self):
        header3 = (
            f"{'Cycle':>8s}"
            " | " + f"{'Sent':>5s} {'Recv':>5s}"
            "   | " + f"{'Sent':>5s} {'Recv':>5s}"
            "   | " + f"{'Sent':>6s} {'Recv':>6s}"
            "   | " + f"{'Sent':>6s} {'Recv':>6s}"
            "   | " + f"{'MSE':>9s} {'PSNR(dB)':>9s}"
            "   | " + f"{'Program':>4s} {'System':>4s}"
        )
        header4 = (
            f"{'':8s}"
            " | " + f"{'AUDIO (msg)':^13s}"
            " | " + f"{'VIDEO (msg)':^13s}"
            " | " + f"{'AUDIO (kbps)':^15s}"
            " | " + f"{'VIDEO (kbps)':^15s}"
            " | " + f"{'VIDEO METRICS':^20s}"
            " |     " + f"{'CPU (%)':^8s}"
        )
        print(header3)
        print(header4)
        print("=" * (8 + 3 + 13 + 3 + 13 + 3 + 15 + 3 + 15 + 3 + 20 + 3 + 8 + 4))

    def calculate_video_metrics(self):
        """Calculate MSE and PSNR between sent and received frames."""
        if self.last_sent_frame is None or self.last_received_frame is None:
            return None, None
        
        try:
            # Convert frames for comparison (ensure same shape and type)
            sent_frame = self.last_sent_frame.astype(np.float32)
            received_frame = self.last_received_frame.astype(np.float32)
            
            # Calculate MSE
            mse = np.mean((sent_frame - received_frame) ** 2)
            
            # Calculate PSNR (Peak Signal-to-Noise Ratio)
            # PSNR = 10 * log10(MAX^2 / MSE)
            if mse > 0:
                psnr = 10.0 * np.log10((np.max(sent_frame) ** 2) / mse)
            else:
                psnr = float('inf')  
            
            return mse, psnr
        except Exception as e:
            logging.debug(f"Error calculating video metrics: {e}")
            return None, None

    def loop_cycle_feedback(self):
        #if not args.show_video or not hasattr(self, 'cap') or self.cap is None:
        #    if hasattr(minimal.Minimal__verbose, 'loop_cycle_feedback'):
        #        return super(Minimal_Video, self).loop_cycle_feedback()
        #    return

        cycle = 1
        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]
        start_time = self._stats_start_time

        self.print_footer()

        while self.running:
            time.sleep(self.seconds_per_cycle) 
            
            now = time.time()
            if self.end_time and now >= self.end_time:
                print(f"\nTime limit reached: {getattr(args, 'reading_time', '?')} seconds")
                self.time_event.set()
                break

            elapsed = max(now - self.old_time, 0.001)
            elapsed_CPU_time = psutil.Process().cpu_times()[0] - self.old_CPU_time
            self.CPU_usage = 100 * elapsed_CPU_time / elapsed
            self.global_CPU_usage = psutil.cpu_percent(interval=None)

            audio_sent_kbps = int(self.sent_bytes_count * 8 / 1000 / elapsed)
            audio_recv_kbps = int(self.received_bytes_count * 8 / 1000 / elapsed)
            video_sent_kbps = int(self.video_sent_bytes_count * 8 / 1000 / elapsed)
            video_recv_kbps = int(self.video_received_bytes_count * 8 / 1000 / elapsed)

            self._total_audio_sent_bytes += self.sent_bytes_count
            self._total_audio_received_bytes += self.received_bytes_count
            self._total_video_sent_bytes += self.video_sent_bytes_count
            self._total_video_received_bytes += self.video_received_bytes_count

            time_info = ""
            if self.end_time:
                elapsed_total = now - start_time
                progress = min(100, 100 * elapsed_total / getattr(args, "reading_time", 1))
                time_info = f" | {elapsed_total:.1f}s/{getattr(args, 'reading_time', '?')}s ({progress:.0f}%)"

            print("\033[3A", end='')
            mse_str = f"{self.last_mse:.2f}"
            psnr_str = f"{self.last_psnr:.2f}"
            print(
                f"{cycle:>8d} |"
                f"{self.sent_messages_count:>5d} {self.received_messages_count:>5d}    |"
                f"{self.video_sent_messages_count:>5d} {self.video_received_messages_count:>5d}    |"
                f"{audio_sent_kbps:>6d} {audio_recv_kbps:>6d}    |"
                f"{video_sent_kbps:>6d} {video_recv_kbps:>6d}    |"
                f"{mse_str:>9s} {psnr_str:>9s}    |"
                f"{int(self.CPU_usage):>4d} {int(self.global_CPU_usage):>6d}       "
                f"{time_info}"
            )
            self.print_footer()

            self.sent_bytes_count = 0
            self.received_bytes_count = 0
            self.sent_messages_count = 0
            self.received_messages_count = 0
            self.video_sent_bytes_count = 0
            self.video_received_bytes_count = 0
            self.video_sent_messages_count = 0
            self.video_received_messages_count = 0

            cycle += 1
            self.old_time = now
            self.old_CPU_time = psutil.Process().cpu_times()[0]

    def print_final_averages(self):
        total_time = time.time() - self._stats_start_time
        if total_time < 0.1:
            print("Duration too short to calculate bandwidth averages.")
            return

        audio_sent_kbps = self._total_audio_sent_bytes * 8 / 1000 / total_time
        audio_received_kbps = self._total_audio_received_bytes * 8 / 1000 / total_time
        video_sent_kbps = self._total_video_sent_bytes * 8 / 1000 / total_time
        video_received_kbps = self._total_video_received_bytes * 8 / 1000 / total_time

        avg_frags = (
            sum(self._fragments_received_history) / len(self._fragments_received_history)
            if self._fragments_received_history else 0
        )

        print("\n=== Global bandwidth statistics ===")
        print(f"Audio sent:       {audio_sent_kbps:.2f} kbps")
        print(f"Audio received:   {audio_received_kbps:.2f} kbps")
        print(f"Video sent:       {video_sent_kbps:.2f} kbps")
        print(f"Video received:   {video_received_kbps:.2f} kbps")
        print(f"Total time:       {total_time:.1f} s")
        print("=====================================")
        
        # Video quality metrics
        if self.frames_analyzed > 0:
            avg_mse = self.accumulated_mse / self.frames_analyzed
            avg_psnr = self.accumulated_psnr / self.frames_analyzed
            print("\n=== Video quality metrics ===")
            print(f"Average MSE (Mean Squared Error):  {avg_mse:.2f}")
            print(f"Average PSNR (dB):                {avg_psnr:.2f} dB")
            print(f"Frames analyzed:                  {self.frames_analyzed}")
            print("===============================")

    def video_loop(self):
        try:
            while self.running:
                data = self.capture_image()
                fragments_received_this_cycle = 0

                # Store the sent frame for metrics (reshape to original frame shape)
                if data:
                    self.last_sent_frame = np.frombuffer(data, dtype=np.uint8).reshape(self.height, self.width, 3).copy()

                for frag_idx in range(self.total_frags):
                    sent_len = self.send_video_fragment(frag_idx, data)
                    self.video_sent_bytes_count += sent_len
                    self.video_sent_messages_count += 1

                    recv_idx, recv_len = self.receive_video_fragment()
                    if recv_len:
                        self.video_received_bytes_count += recv_len
                        self.video_received_messages_count += 1
                        fragments_received_this_cycle += 1

                # Store received frame for metrics after all fragments processed
                self.last_received_frame = self.remote_frame.copy()
                
                # Calculate and accumulate video quality metrics (MSE/PSNR)
                mse, psnr = self.calculate_video_metrics()
                if mse is not None:
                    self.last_mse = mse
                    self.last_psnr = psnr if psnr != float('inf') else 100  # Cap PSNR at 100 dB
                    self.accumulated_mse += mse
                    self.accumulated_psnr += self.last_psnr
                    self.frames_analyzed += 1

                self._fragments_received_this_cycle = fragments_received_this_cycle
                self.show_video()
        except Exception as e:
            logging.error(f"Error in video loop: {e}")
            pass


    def run(self):
        #if not args.show_video or not hasattr(self, 'cap') or self.cap is None:
        #    print("Video disabled. Running audio-only mode in verbose.")
        #    minimal.Minimal__verbose.run(self)
        #    return

        #if not hasattr(self, 'loop_cycle_feedback'):
        #    print("Warning: Statistics feedback loop is not available. Running without statistics.")
        #    super().run()
        #    return

        print("Starting video with unified loop and simplified protocol (verbose)...")
        print("Press Ctrl+C to terminate\n")
        self.print_header()

        cycle_feedback_thread = threading.Thread(target=self.loop_cycle_feedback, daemon=True, name="FeedbackThread")
        cycle_feedback_thread.start()

        t_unified = threading.Thread(target=self.video_loop, daemon=True, name="UnifiedVideoThread")
        t_unified.start()

        try:
            minimal.Minimal.run(self)
        except KeyboardInterrupt:
            print("Keyboard interrupt detected.")
        finally:
            self.running = False
            if cycle_feedback_thread.is_alive():
                cycle_feedback_thread.join(timeout=1)
            if t_unified.is_alive():
                t_unified.join(timeout=1)
            if self.cap and self.cap.isOpened():
                self.cap.release()
            cv2.destroyAllWindows()
            if hasattr(self, 'video_sock') and self.video_sock:
                self.video_sock.close()
            print("Video application stopped.")

if __name__ == "__main__":
    try:
        import argcomplete
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        pass
    args = minimal.parser.parse_args()
    if not hasattr(args, 'destination_address') or not args.destination_address:
        args.destination_address = "localhost"

    verbose_enabled = (getattr(args, 'show_stats', False) or
                       getattr(args, 'show_samples', False) or
                       getattr(args, 'show_spectrum', False))
    verbose_class_exists = hasattr(minimal, 'Minimal__verbose')

    if verbose_enabled and verbose_class_exists:
        print("Starting in Verbose mode...")
        intercom_app = Minimal_Video__verbose()
    elif verbose_enabled and not verbose_class_exists:
        print("Warning: Verbose mode enabled but minimal.Minimal__verbose not found. Running without statistics.")
        intercom_app = Minimal_Video()
    else:
        intercom_app = Minimal_Video()

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
