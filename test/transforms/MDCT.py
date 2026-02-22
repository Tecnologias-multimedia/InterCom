#!/usr/bin/env python3
"""Plot the live microphone signal(s) using MDCT with matplotlib.

Matplotlib, NumPy, and sounddevice have to be installed.
"""
import argparse
import queue
import sys
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-i', '--interval', type=float, default=0,
    help='minimum time between plot updates (default: %(default)s ms)')
parser.add_argument(
    '-b', '--blocksize', type=int, default=1024, help='block size (in samples)')
parser.add_argument(
    '-r', '--samplerate', type=float, default=44100, help='sampling rate of audio device')
parser.add_argument(
    'channels', type=int, default=[1, 2], nargs='*', metavar='CHANNEL',
    help='input channels to plot (default: the first)')
args = parser.parse_args()

if any(c < 1 for c in args.channels):
    parser.error('argument CHANNEL: must be >= 1')
mapping = [c - 1 for c in args.channels]  # Channel numbers start with 1
q = queue.Queue()

# --- MDCT Pre-computations ---
N = args.blocksize
print("MDCT blocksize (N) =", N)

n_idx = np.arange(2 * N)
k_idx = np.arange(N)

# Sine window for perfect reconstruction and spectral smoothing
window = np.sin(np.pi / (2 * N) * (n_idx + 0.5))

# MDCT Basis matrix. Scaled by 2.0/N so pure tones stay roughly within [-1, 1] plot limits.
mdct_basis = (2.0 / N) * np.cos(np.pi / N * (n_idx[None, :] + 0.5 + N / 2.0) * (k_idx[:, None] + 0.5))

# MDCT requires a 50% overlap, which corresponds to exactly one blocksize
prev_chunk = np.zeros((N, len(args.channels)), dtype=np.float32)

def audio_callback(indata, frames, time, status):
    """This is called for each audio block by sounddevice."""
    global prev_chunk
    
    # Extract only the requested channels
    current_chunk = indata[:, mapping]
    
    # MDCT takes 2N samples to produce N coefficients
    combined = np.concatenate((prev_chunk, current_chunk), axis=0)
    prev_chunk = current_chunk.copy()
    
    # Apply the sine window
    windowed = combined * window[:, None]
    
    # Compute MDCT using matrix multiplication (very fast for typical block sizes)
    # mdct_basis is (N, 2N), windowed is (2N, C) -> result is (N, C)
    mdct_coeffs = np.dot(mdct_basis, windowed)
    
    # Queue expects shape (Channels, N)
    q.put(mdct_coeffs.T)

def update_plot(frame):
    """This is called by matplotlib for each plot update."""
    global plotdata
    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break
            
        # Transpose back from (C, N) to (N, C) for plotting
        plotdata = data.T 

    for column, line in enumerate(lines):
        line.set_ydata(plotdata[:, column])
    return lines

try:
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    if args.samplerate is None:
        device_info = sd.query_devices(args.device, 'input')
        args.samplerate = device_info['default_samplerate']

    plotdata = np.zeros((args.blocksize, len(args.channels)))

    fig, ax = plt.subplots()
    lines = ax.plot(plotdata)
    if len(args.channels) > 1:
        ax.legend(['channel {}'.format(c) for c in args.channels],
                  loc='lower left', ncol=len(args.channels))
                  
    ax.axis((0, len(plotdata), -1, 1))
    ax.set_yticks([0])
    ax.yaxis.grid(True)
    ax.tick_params(bottom=False, top=False, labelbottom=False,
                   right=False, left=False, labelleft=False)
    fig.tight_layout(pad=0)

    print("samplerate =", args.samplerate)

    # Note: explicitly setting dtype to float32 so values stay in the [-1.0, 1.0] range
    stream = sd.InputStream(
        device=args.device, channels=max(args.channels), blocksize=args.blocksize,
        samplerate=args.samplerate, callback=audio_callback, dtype=np.float32)
        
    ani = FuncAnimation(fig, update_plot, interval=args.interval, blit=True)
    
    with stream:
        plt.show()

except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
