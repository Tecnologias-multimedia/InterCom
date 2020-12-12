import argparse
import numpy as np
import buffer
from buffer import minimal
import struct
import argcomplete  # <tab> completion for argparse.
import zlib
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

    integer_data = struct.unpack(fmt, raw_data)
    del raw_data

    data = np.reshape(integer_data, (num_frames, num_channels))

    return data, num_frames


# Tell the parser to add an argument for the compression level
minimal.parser.add_argument("-y", "--compression_level", type=int, default=6, help="Compression level [1-9]")
# and another argument in case we want to use a sample
minimal.parser.add_argument("-f", "--file_sample", type=str, default=None, help="Sample (wav file) to be used for benchmarking")

class Compress(buffer.Buffering):

    def __init__(self):
        super().__init__()

        sample = minimal.args.file_sample
        self.benchmark = False
        self.c_level = minimal.args.compression_level
        self.average_c_ratio = 0.0

        if sample:
            print("benchmarking = enabled")
            print("Reading sample... This could take a while...")
            self.sampledata, self.sampleframes = pcm_channels(sample)
            self.benchmark = True
            self.c_level = 1
            self.chunk_index = 0

        print(f"compression_level = {self.c_level}")

    # We reorder, compress and pack the data
    def pack(self, chunk_number, chunk):

        # Number of frames
        frames = minimal.args.frames_per_chunk
        # Number of frames if there was only one channel
        total_frames = frames * self.NUMBER_OF_CHANNELS

        # Reordered data, each channel is located in the
        # first and second halves of the array respectively
        r_chunk = np.empty(total_frames, dtype='int16')

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
          
        chunk = chunk.flatten()

        r_chunk[:frames] = chunk[::2]
        r_chunk[frames:] = chunk[1::2]

        # Let's compress the data!
        c_chunk = zlib.compress(r_chunk, level=self.c_level)

        # Save the current ratio if we are benchmarking
        if self.benchmark:
            self.average_c_ratio += len(c_chunk) / 2 / total_frames

        # Time to show our results !
        if end:
            print(f"La media del ratio de compresión en el nivel {self.c_level} es de {self.average_c_ratio/self.chunk_index}")
            # We reset all of the values
            self.chunk_index = 0
            self.average_c_ratio = 0.0
            self.c_level += 1 # And increase our compression level

            # Have we reached the limit ? If so
            # we stop bencharmking
            if self.c_level > 9:
                print("Hemos acabado de tomar medidas.")
                self.c_level = -1
                self.benchmark = False

        # We pack the compressed data and the chunk_number
        packed_chunk = struct.pack("!H", chunk_number) + c_chunk

        return packed_chunk

    # We unpack, decompress & reorder the data
    def unpack(self, packed_chunk,
               dtype=buffer.minimal.Minimal.SAMPLE_TYPE):

        # Number of frames
        frames = minimal.args.frames_per_chunk

        # Number of frames if there was only one channel
        total_frames = frames * self.NUMBER_OF_CHANNELS

        # We extract the chunk number
        (chunk_number,) = struct.unpack("!H", packed_chunk[:2])

        # We extract the compressed data
        c_chunk = packed_chunk[2:]

        # Time to decompress our audio!
        d_chunk = zlib.decompress(c_chunk)

        # We convert our bytes object into an array
        chunk = np.frombuffer(d_chunk, dtype='int16')

        # Reordered data, each channel is located in the
        # first and second halves of the array respectively
        reordered_chunk = np.empty(total_frames, dtype='int16')

        reordered_chunk[::2] = chunk[:frames]
        reordered_chunk[1::2] = chunk[frames:]

        reordered_chunk = reordered_chunk.reshape((-1, 2))

        return chunk_number, reordered_chunk


if __name__ == "__main__":

    minimal.parser.description = __doc__
    argcomplete.autocomplete(minimal.parser)
    minimal.args = minimal.parser.parse_known_args()[0]
    intercom = Compress()
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        minimal.parser.exit(1)
