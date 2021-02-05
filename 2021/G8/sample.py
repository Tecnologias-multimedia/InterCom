import wave
import numpy as np
import struct

# https://github.com/haloboy777/wav-to-pcm/blob/master/pcm_channels.py
def pcm_channels(wave_file):
    stream = wave.open(wave_file,"rb")

    num_channels = stream.getnchannels()
    sample_rate = stream.getframerate()
    sample_width = stream.getsampwidth()
    num_frames = stream.getnframes()

    if sample_rate != 44100:
        raise ValueError("This test is only meant for 44100 Hz")

    raw_data = stream.readframes( num_frames )
    stream.close()

    total_samples = num_frames * num_channels

    if sample_width == 2:
        fmt = "%ih" % total_samples
    else:
        raise ValueError("This test is only meant for 16 bit audio formats.")

    integer_data = struct.unpack(fmt, raw_data)
    del raw_data

    data = np.reshape(integer_data, (num_frames, num_channels))

    return data, num_frames
