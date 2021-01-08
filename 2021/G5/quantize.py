import numpy as np
import struct
import zlib
from time import time
from math import ceil, floor
import compress
import wave
from compress import minimal
import argcomplete  # <tab> completion for argparse.

"""
This is a brief description/example of how our program regulates the step value.
================================================================================

NOTE: Our program works under the assumption that both upload and download speeds 
are symmetric.

Let's take the following example: PC1 and PC2 are in different networks with a 
bandwidth of 300/300 kbps and 500/500 kbps respectively. The audio that each 
client is transmitting has a bitrate of 1000 kbps.

       PC1         PC1 will still receive 300         PC2
    +-------+         <-------------------         +-------+
    |       |                                      |       |
    |       |                                      |       |
    +-------+         ------------------->         +-------+
     300/300        PC2 will only receive 300       500/500

Our program, running in PC1, will see that the client is receiving 300 kbps and sending 
1000 kbps and therefore will adjust the step value since it believes that the
network is limited to 300/300. Even though PC2 is also sending at 1000 kbps (initially),
PC1 will still receive 300 kbps (again we are limited by the network).

PC2 will see that the audio being sent is not equal to the audio that is being received
(even though the network is better 500 > 300, it will still receive 300 kbps) and adjust
the step value accordingly. Taking into account that the higher the step value, the higher
the chance of compressing the data at a higher rate, we have to use the following formula:

    self.step_level * self.sent_kbps / self.received_kbps

This means that the rate at which the data is being sent (and received) will be limited
by the slowest client out of the two (PC1 in this example).

It's important to note that since both clients might be sending different data (at different
bitrates) and using different step values, we must include the step value alongside the
chunk number and the audio itself (that way the the recipient can decode the audio correctly).

"""

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
# Tell the parser to add an argument for the step of our quantize function
minimal.parser.add_argument("-q", "--quantization_level", type=int, default=0, help="Step level [1-32767]")

class BR_Control(compress.Compression__verbose):

    def __init__(self):
        super().__init__()

        # Previous milestone...
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

        # Milestone 10
        self.variable_step = True if minimal.args.quantization_level == 0 else False
        self.step_level = 64 if self.variable_step else minimal.args.quantization_level
        self.last_change = time()

        print(f"step_level = {self.step_level}")
        print(f"compression_level = {self.c_level}")

    # We reorder, quantizate, compress and pack the data
    def pack(self, chunk_number, chunk):

        # Is our step level going to fluctuate depending on the bitrate ?
        if self.variable_step:

            # If we have a value for received kbps, the received and sent values
            # differ and a second has passed, we change the quantization step
            if self.received_kbps and self.received_kbps != self.sent_kbps and time() - self.last_change >= 1:
                self.step_level = ceil(self.step_level * self.sent_kbps / self.received_kbps)
                self.last_change = time()

            # If the received and sent values have
            # stabilized we increase our bitrate
            # (only for local playback)
            if time() - self.last_change >= 4:
                self.step_level = max(1, floor(self.step_level * 0.99))
        
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
        # Here we divide our data by the step level
        chunk = (chunk / self.step_level).astype(np.int)

        r_chunk[:frames] = chunk[::2]
        r_chunk[frames:] = chunk[1::2]

        # Let's compress the data!
        c_chunk = zlib.compress(r_chunk, level=self.c_level)

        # Save the current ratio if we are benchmarking
        if self.benchmark:
            self.average_c_ratio += len(c_chunk) / 2 / total_frames

        # Time to show our results !
        if end:
            print(f"\nLa media del ratio de compresión en el nivel {self.c_level} es de {self.average_c_ratio/self.chunk_index}\n")
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

        # We pack the compressed data, step level and the chunk_number
        # We need to send the step level because the receivers step level might differ
        packed_chunk = struct.pack("!HH", chunk_number, self.step_level) + c_chunk

        return packed_chunk
        
        

    # We unpack, decompress & reorder the data
    def unpack(self, packed_chunk,
               dtype=compress.minimal.Minimal.SAMPLE_TYPE):
        
        # Number of frames
        frames = minimal.args.frames_per_chunk

        # Number of frames if there was only one channel
        total_frames = frames * self.NUMBER_OF_CHANNELS

        # We extract the chunk number
        (chunk_number, q_step) = struct.unpack("!HH", packed_chunk[:4])

        # We extract the compressed data
        c_chunk = packed_chunk[4:]

        # Time to decompress our audio!
        d_chunk = zlib.decompress(c_chunk)

        # We convert our bytes object into an array
        chunk = np.frombuffer(d_chunk, dtype='int16')

        # Reordered data, each channel is located in the
        # first and second halves of the array respectively
        reordered_chunk = np.empty(total_frames, dtype='int16')

        # We need to calculate the length of each channel to
        # correctly display the data in our output
        len_compressed_channel_0 = len(chunk[:frames])
        reordered_chunk[::2] = chunk[:frames]
        len_compressed_channel_1 = len(chunk[frames:])
        reordered_chunk[1::2] = chunk[frames:]

        reordered_chunk = reordered_chunk.reshape((-1, 2))
        # We multiply the reordered_chunk by the senders step level
        dequantized_chunk = reordered_chunk * q_step

        self.bps[0] += len_compressed_channel_0*8
        self.bps[1] += len_compressed_channel_1*8

        return chunk_number, dequantized_chunk

        
if __name__ == "__main__":

    minimal.parser.description = __doc__
    argcomplete.autocomplete(minimal.parser)
    minimal.args = minimal.parser.parse_known_args()[0]
    intercom = BR_Control()
    try:
        intercom.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        minimal.parser.exit(1)
