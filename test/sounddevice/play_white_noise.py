#!/usr/bin/env python3
"""Play white uniform random noise."""
import argparse
import sys
import numpy as np
import sounddevice as sd

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()

if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)

parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='output device (numeric ID or substring)')
parser.add_argument(
    '-a', '--amplitude', type=float, default=0.2,
    help='amplitude/peak level (default: %(default)s)')
args = parser.parse_args(remaining)

try:
    # Query the sample rate of the chosen device
    device_info = sd.query_devices(args.device, 'output')
    samplerate = device_info['default_samplerate']

    def callback(outdata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        
        # Generate uniform random numbers between -amplitude and +amplitude
        # size=(frames, 1) ensures it matches the outdata shape (samples, channels)
        noise = np.random.uniform(-args.amplitude, args.amplitude, size=(frames, 1))
        
        outdata[:] = noise

    with sd.OutputStream(device=args.device, channels=1, callback=callback,
                         samplerate=samplerate):
        print('#' * 80)
        print(f"Playing White Uniform Noise at {samplerate} Hz")
        print(f"Amplitude Range: [-{args.amplitude}, {args.amplitude}]")
        print('Press Return to quit')
        print('#' * 80)
        input()

except KeyboardInterrupt:
    parser.exit('\nInterrupted by user')
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
