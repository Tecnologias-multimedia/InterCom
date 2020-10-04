#!/usr/bin/env python3
"""Plot the live microphone signal(s) with matplotlib.

Matplotlib and NumPy have to be installed.

"""
import argparse
import queue
import sys
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
import pywt

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(description=__doc__)
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

_0_chunk = np.zeros(
    (args.blocksize, len(args.channels)), dtype=np.int16)
_1_chunk = np.zeros(
    (args.blocksize, len(args.channels)), dtype=np.int16)
_2__chunk = np.zeros(
    (args.blocksize, len(args.channels)), dtype=np.int16)

kernel = "db5"
wavelet = pywt.Wavelet(kernel)
levels = 1
number_of_overlaped_samples = wavelet.dec_len * levels

def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    global _0_chunk
    global _1_chunk
    global _2_chunk

    #  _0_chunk      _1_chunk      _2_chunk
    # +-------------+-------------+-----------+
    # | indata[t-1] | indata[t-1] | indata[t] |
    # +-------------+-------------+-----------+
    _0_chunk = _1_chunk
    _1_chunk = _2_chunk
    _2_chunk = indata

    # extended_chunk:
    # +----+--------+----+
    # : c0 |   c1   | c2 :
    # +----+--------+----+
    extended_chunk = np.concatenate(
        (_0_chunk[args.blocksize-number_of_overlaped_samples:],
         _1_chunk,
         _2_chunk[:number_of_overlaped_samples]), axis=0)
    print(number_of_overlaped_samples, extended_chunk.shape)
    coeffs = [None]*len(args.channels)
    for c in range(len(args.channels)):
        coeffs_ = pywt.wavedec(extended_chunk[:, c], wavelet=kernel, level=levels, mode="per")
        nos = number_of_overlaped_samples
        for i in range(len(coeffs_)-1, 0, -1):
            nos >>= 1
            coeffs_[i] = coeffs_[i][nos:len(coeffs_[i])-nos]
            print(nos, len(coeffs_[i])-nos)
        coeffs_[0] = coeffs_[0][nos:len(coeffs_[0])-nos]
        coeffs[c], slices = pywt.coeffs_to_array(coeffs_)
        #print(coeffs[c].shape)
        #coeffs[c] = 20*np.log10(coeffs[c]+1)
    both_channels = np.stack(coeffs)
    q.put(both_channels)

def update_plot(frame):
    """This is called by matplotlib for each plot update.

    Typically, audio callbacks happen more frequently than plot updates,
    therefore the queue tends to contain multiple blocks of audio data.

    """
    global plotdata
    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break
        shift = len(data[0])
        plotdata = np.empty((shift*len(args.channels), ))
        plotdata[0::2] = data[0, :]
        plotdata[1::2] = data[1, :]
        plotdata = plotdata.reshape((shift, len(args.channels)))
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

    stream = sd.InputStream(
        device=args.device, channels=max(args.channels), blocksize=args.blocksize,
        samplerate=args.samplerate, callback=audio_callback)
    #ani = FuncAnimation(fig, update_plot, interval=args.interval, blit=True)
    with stream:
        #plt.show()
        input()
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
