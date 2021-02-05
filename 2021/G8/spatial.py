import numpy as np
import math
import threading
import time
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import br_control
from enum import Enum
from struct import unpack
import wave

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

    integer_data = unpack(fmt, raw_data)
    del raw_data

    data = np.reshape(integer_data, (num_frames, num_channels))

    return data, num_frames

# Type of filters our program supports
class Filter(Enum):
    NONE = 0
    MST = 1
    KLT = 2
    ST = 3

# argument in case we want to use a sample
br_control.minimal.parser.add_argument("-f", "--file_sample", type=str, default=None, help="Sample (wav file) to be used for benchmarking")

class Spatial_decorrelation(br_control.BR_Control__verbose):

    def __init__(self):

        # [ Type of filter, Analyze fn of that filter ]
        self.Filter_Analyze = {
            Filter.NONE: (lambda arg : arg),
            Filter.MST: self.MST_analyze,
            Filter.KLT: self.KLT_analyze,
            Filter.ST: self.ST_analyze
        }

        # [ Type of filter, Synthetize fn of that filter ]
        self.Filter_Synthetize = {
            Filter.NONE: (lambda arg : arg),
            Filter.MST: self.MST_synthesize,
            Filter.KLT: self.KLT_synthesize,
            Filter.ST: self.ST_synthesize
        }

        # Filter that the program uses by default
        self.filter = Filter.NONE
        
        self.benchmark = False
        self.average_c_ratio = 0.0
        sample = br_control.minimal.args.file_sample

        if sample:
            print("benchmarking = enabled")
            print("Reading sample... This could take a while...")
            self.sampledata, self.sampleframes = pcm_channels(sample)
            self.benchmark = True
            self.chunk_index = 0

        super().__init__()

    # Analysis transform:
    #
    #  [w[0]] = [1  1] [x[0]]
    #  [w[1]]   [1 -1] [x[1]]

    def MST_analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1] # L(ow frequency subband)
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1] # H(igh frequency subband)
        return w

    # Inverse transform:
    #
    #  [x[0]] = 1/2 [1  1] [w[0]]
    #  [x[1]]       [1 -1] [w[1]]

    def MST_synthesize(self, w):
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = (w[:, 0] + w[:, 1])/2 # L(ow frequency subband)
        x[:, 1] = (w[:, 0] - w[:, 1])/2 # H(igh frequency subband)
        return x

    # KLT analysis transform:
    #
    #  [w[0]] = 1/sqrt(2) [1  1] [x[0]]
    #  [w[1]]             [1 -1] [x[1]]

    def KLT_analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = np.rint((x[:, 0].astype(np.int32) + x[:, 1]) / math.sqrt(2)) # L
        w[:, 1] = np.rint((x[:, 0].astype(np.int32) - x[:, 1]) / math.sqrt(2)) # H
        return w

    # Synthesis transform:
    #
    #  [x[0]] = 1/sqrt(2) [1  1] [w[0]]
    #  [x[1]]             [1 -1] [w[1]]

    def KLT_synthesize(self, w):
        x = np.empty_like(w, dtype=np.int16)
        #x[:, 0] = np.rint((w[:, 0] + w[:, 1]) / math.sqrt(2)) # L(ow frequency subband)
        #x[:, 1] = np.rint((w[:, 0] - w[:, 1]) / math.sqrt(2)) # H(igh frequency subband)
        x[:, :] = self.KLT_analyze(w)
        return x

    # Forward transform:
    #
    #  w[0] = ceil((x[0] + x[1])/2)
    #  w[1] = x[0] - x[1] 
    #
    # Inverse transform:
    #
    #  x[0] = w[0] + ceil((w[1]+1)/2)
    #  x[1] = x[0] - w[1]

    def ST_analyze(self, x):
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = np.ceil((x[:, 0].astype(np.int32) + x[:, 1])/2)
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1]
        return w

    def ST_synthesize(self, w):
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = w[:, 0] + np.ceil((w[:, 1] + 1)/2)
        x[:, 1] = x[:, 0] - w[:, 1]
        return x

    def pack(self, chunk_number, chunk):

        # Number of frames
        frames = br_control.minimal.args.frames_per_chunk
        # Number of frames if there was only one channel
        total_frames = frames * self.NUMBER_OF_CHANNELS

        end = False

        if self.benchmark:

            # What section of the sample do we need to get ?
            index = self.chunk_index * frames
            next_index = index+frames

            # Have we reached the end of the sample ?
            # if so, show the results
            end = (next_index >= self.sampleframes)

            frames_copied = self.sampleframes % frames if end else frames
            chunk[0:frames_copied] = self.sampledata[index:next_index]
            chunk[frames_copied:] = 0
            self.chunk_index += 1

        chunk = self.Filter_Analyze[self.filter](chunk)
        packed_chunk = super().pack(chunk_number, chunk)

        # Save the current ratio if we are benchmarking
        if self.benchmark:
            self.average_c_ratio += (len(packed_chunk) - 4) / 2 / total_frames

        # Time to show our results !
        if end:
            print(f"\nLa media del ratio de compresión con {self.filter} es de {self.average_c_ratio/self.chunk_index}\n")
            # We reset all of the values
            self.average_c_ratio = 0
            self.chunk_index = 0

            # If we have finished taking measures with the current
            # filter let's move on to the next one
            if self.filter.value < len(Filter) - 1:
                self.filter = Filter(self.filter.value+1)
            # If there isn't one, we stop benchmarking
            else:
                self.benchmark = False

        return packed_chunk

    def unpack(self, packed_chunk):
        chunk_number, chunk = super().unpack(packed_chunk, dtype='int16')
        chunk = self.Filter_Synthetize[self.filter](chunk)
        return chunk_number, chunk


if __name__ == "__main__":
    br_control.minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(br_control.minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    br_control.minimal.args = br_control.minimal.parser.parse_args()
    
    intercom = Spatial_decorrelation()

    try:
        intercom.run()
    except KeyboardInterrupt:
        br_control.minimal.parser.exit("\nInterrupted by user")
