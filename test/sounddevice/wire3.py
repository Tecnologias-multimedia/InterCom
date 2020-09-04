import argparse
import logging
import threading
import sounddevice as sd

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('-i', '--input-device', type=int_or_str,
                    help='input device ID or substring')
parser.add_argument('-o', '--output-device', type=int_or_str,
                    help='output device ID or substring')
parser.add_argument('-c', '--channels', type=int, default=2,
                    help='number of channels')
parser.add_argument('-t', '--dtype', help='audio data type')
parser.add_argument('-s', '--samplerate', type=float, help='sampling rate')
parser.add_argument('-b', '--blocksize', type=int, help='block size')
parser.add_argument('-l', '--latency', type=float, help='latency in seconds')
args = parser.parse_args()

sd.default.samplerate = samplerate=args.samplerate
sd.default.channels = args.channels

def play(buf):
    sd.play(buf)

def record():
    buf = sd.rec(blocksize=args.blocksize)
    return buf

for i in range(1000):
    chunk = sd.Stream.read(sd, frames=1024)
    sd.Stream.write(chunk)
