#!/usr/bin/env python3
"""Plot live Wavelet Packet subband variance from microphone signal."""

import argparse
import queue
import sys
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Qt5Agg")   # sudo pacman -S python-pyqt5; pip install PyQt5
import numpy as np
import sounddevice as sd
import pywt
import math


def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text


# -------------------- ARGUMENTS --------------------

parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

parser.add_argument('-l', '--list-devices', action='store_true',
                    help='show list of audio devices and exit')
parser.add_argument('-d', '--device', type=int_or_str,
                    help='input device (numeric ID or substring)')
parser.add_argument('-i', '--interval', type=float, default=30,
                    help='minimum time between plot updates (ms)')
parser.add_argument('-b', '--blocksize', type=int, default=1024,
                    help='block size (in samples)')
parser.add_argument('-r', '--samplerate', type=float, default=44100,
                    help='sampling rate')
parser.add_argument('-v', '--levels', type=int, default=6,
                    help='number of Wavelet Packet levels')
parser.add_argument('-w', '--wavelet', type=str, default="db5",
                    help=f'wavelet name from {pywt.wavelist()}')
parser.add_argument('channels', type=int, default=[1, 2], nargs='*',
                    metavar='CHANNEL',
                    help='input channels to plot (default: first two)')

args = parser.parse_args()

if any(c < 1 for c in args.channels):
    parser.error('argument CHANNEL: must be >= 1')

mapping = [c - 1 for c in args.channels]
q = queue.Queue()


# -------------------- WAVELET SETUP --------------------

wavelet = pywt.Wavelet(args.wavelet)

if args.levels > 0:
    overlaped_area_size = wavelet.dec_len * args.levels
    overlaped_area_size = 1 << math.ceil(
        math.log(overlaped_area_size) / math.log(2)
    )
else:
    overlaped_area_size = 0

num_bands = 2 ** args.levels

prev_chunk = np.zeros((args.blocksize, len(args.channels)))
prev_overlaped_area = np.zeros((overlaped_area_size, len(args.channels)))


# -------------------- AUDIO CALLBACK --------------------

def audio_callback(indata, frames, time, status):
    global prev_overlaped_area, prev_chunk

    extended_chunk = np.concatenate(
        (prev_overlaped_area,
         prev_chunk,
         indata[0:overlaped_area_size]),
        axis=0
    )

    prev_overlaped_area = prev_chunk[
        args.blocksize - overlaped_area_size: args.blocksize
    ]

    prev_chunk = indata.copy()

    coeffs = [None] * len(args.channels)

    for c in range(len(args.channels)):
        wp = pywt.WaveletPacket(
            data=extended_chunk[:, c],
            wavelet=wavelet,
            maxlevel=args.levels,
            mode="per"
        )

        nodes = wp.get_level(args.levels, order="freq")

        subband_vars = []

        for node in nodes:
            offset = overlaped_area_size // (2 ** args.levels)

            if offset > 0:
                sliced = node.data[offset:-offset]
            else:
                sliced = node.data

            if len(sliced) > 0:
                # log variance gives better visualization stability
                subband_vars.append(np.log1p(np.var(sliced)))
                #subband_vars.append(np.var(sliced))
            else:
                subband_vars.append(0.0)

        coeffs[c] = np.array(subband_vars)

    both_channels = np.stack(coeffs)
    q.put(both_channels)


# -------------------- PLOT UPDATE --------------------

def update_plot(frame):
    global plotdata

    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break

        # data shape: (channels, bands)
        plotdata = data.T

    for column, line in enumerate(lines):
        line.set_ydata(plotdata[:, column])

    return lines


# -------------------- MAIN --------------------

try:
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)

    if args.samplerate is None:
        device_info = sd.query_devices(args.device, 'input')
        args.samplerate = device_info['default_samplerate']

    plotdata = np.zeros((num_bands, len(args.channels)))

    fig, ax = plt.subplots()
    lines = ax.plot(plotdata)

    if len(args.channels) > 1:
        ax.legend(
            ['channel {}'.format(c) for c in args.channels],
            loc='upper right'
        )

    ax.set_xlim(0, num_bands - 1)
    ax.set_ylim(0, 5)  # adjust if needed
    ax.set_xlabel("Wavelet Packet Subband Index")
    ax.set_ylabel("Log(Variance)")
    ax.grid(True)

    fig.tight_layout()

    stream = sd.InputStream(
        device=args.device,
        channels=max(args.channels),
        blocksize=args.blocksize,
        samplerate=args.samplerate,
        callback=audio_callback
    )

    ani = FuncAnimation(
        fig,
        update_plot,
        interval=args.interval,
        blit=True,
        cache_frame_data=False   # ← add this
    )

    with stream:
        plt.show()

except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
