#!/usr/bin/env python3
"""Plot the live microphone signal(s) with matplotlib.

Matplotlib and NumPy have to be installed.

"""
import argparse
import queue
import sys

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
    '-b', '--blocksize', type=int, default=512, help='block size (in samples)')
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


def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    flat = indata.flatten()
    l = indata.shape[0]>>1
    coeffs = np.fft.rfft(flat)
    #print(coeffs.shape)
    spectrum = np.sqrt(coeffs.real*coeffs.real + coeffs.imag*coeffs.imag)
    #spectrum = abs(coeffs)
    #coeffs_, slices = pywt.coeffs_to_array(coeffs)
    #coeffs_ = coeffs[:l].reshape((l,1))
    #coeffs_ = coeffs_.flatten()[:shift]
    #print(type(indata), type(coeffs_))
    #print(indata[10][0], coeffs_[10], mapping)
    #print(indata[::args.downsample, mapping].shape)
    #plotdata[-shift:, :] = coeffs_[0]
    #print(plotdata[-shift:, :])

    # Fancy indexing with mapping creates a (necessary!) copy:
    #q.put(indata[::args.downsample, mapping])
    q.put(spectrum)

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
        shift = len(data)
        #plotdata = np.roll(plotdata, -shift, axis=0)
        #plotdata[-shift:, :] = data.reshape((shift, len(args.channels)))
        plotdata = data.reshape((shift, len(args.channels)))
    for column, line in enumerate(lines):
        line.set_ydata(plotdata[:, column])
    return lines

try:
    import matplotlib
    from matplotlib.animation import FuncAnimation
    import matplotlib.pyplot as plt
    import numpy as np
    import sounddevice as sd
    import pywt

    matplotlib.use('Qt5Agg')  # 'TkAgg' or 'Qt5Agg', or 'MacOSX' on macOS

    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    if args.samplerate is None:
        device_info = sd.query_devices(args.device, 'input')
        args.samplerate = device_info['default_samplerate']

    #length = int(args.window * args.samplerate / (1000 * args.downsample))
    length = 1024
    plotdata = np.zeros((length//2+1, len(args.channels)))

    fig, ax = plt.subplots()
    lines = ax.plot(plotdata)
    if len(args.channels) > 1:
        ax.legend(['channel {}'.format(c) for c in args.channels],
                  loc='lower left', ncol=len(args.channels))
    ax.axis((0, len(plotdata), 0, 1))
    ax.set_yticks([0])
    ax.yaxis.grid(True)
    ax.tick_params(bottom=False, top=False, labelbottom=False,
                   right=False, left=False, labelleft=False)
    fig.tight_layout(pad=0)

    stream = sd.InputStream(
        device=args.device, channels=max(args.channels), blocksize=length,
        samplerate=args.samplerate, callback=audio_callback)
    ani = FuncAnimation(fig, update_plot, interval=args.interval, blit=True)
    with stream:
        plt.show()
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
