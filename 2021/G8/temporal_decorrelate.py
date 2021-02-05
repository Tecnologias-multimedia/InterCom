import intra_frame_decorrelation as ifd
import pywt
import numpy as np
import zlib
import struct
from math import ceil, log, sqrt
from sample import pcm_channels
try:
    import argcomplete
except ImportError:
    print("Unable to import argcomplete")

ifd.minimal.parser.add_argument("-f", "--file_sample", type=str, default=None, help="Sample (wav file) to be used for benchmarking")

class Temporal_decorrelation(ifd.Intra_frame_decorrelation__verbose):

    SAMPLE_TYPE = 'int16'

    def __init__(self):
        super().__init__()

        # Previous milestone...
        sample = ifd.minimal.args.file_sample
        self.benchmark = False
        self.average_c_ratio = 0.0

        if sample:
            print("benchmarking = enabled")
            print("Reading sample... This could take a while...")
            self.sampledata, self.sampleframes = pcm_channels(sample)
            self.benchmark = True
            self.chunk_index = 0

        self.levels = 3 # Levels that our Wavelet will have
        self.filters = ["db5", "haar", "sym5", "coif5", "bior1.5", "rbio1.5", "dmey"]
        self.selected_filter = 0 # Type of filter
        self.signal_mode_ext = "per" # Signal mode extension
        self.wavelet = pywt.Wavelet(self.filters[self.selected_filter]) # Our wavelet

        self.avg_RMSE = 0.0

        # Number of overlapped values according to our level and wavelet
        self.n_el_olapped = 1 << ceil(log(self.wavelet.dec_len * self.levels) / log(2))

        # We store the previous, current and next chunks (these will be used to calculate lapped transforms)
        self.prev_chunk = np.zeros((ifd.minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype='int16')
        self.curr_chunk = np.zeros((ifd.minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype='int16')
        self.next_chunk = np.zeros((ifd.minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype='int16')

    def pack(self, chunk_number, chunk):

        # Number of frames
        frames = ifd.minimal.args.frames_per_chunk
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

        # chunk = self.analyze(chunk)
        transformed_chunk = self.transform_and_quantize(chunk)
        compressed_chunk = zlib.compress(transformed_chunk)

        # Save the current ratio if we are benchmarking
        if self.benchmark:
            self.average_c_ratio += len(compressed_chunk) / 2 / total_frames

            # Buffer we will use to store the current chunk
            rec_curr_chunk = np.empty((frames, self.NUMBER_OF_CHANNELS), dtype='int16')
            rec_chunk = self.dequantize_and_detransform(transformed_chunk)
            # Left channel
            rec_curr_chunk[:,0] = rec_chunk[self.n_el_olapped:frames + self.n_el_olapped]
            # Right channel
            rec_curr_chunk[:,1] = rec_chunk[frames+(3*self.n_el_olapped):(2*frames)+(3*self.n_el_olapped)]

            # Important! We have to compare with the current chunk (since we have
            # an artificial delay built-in)
            self.avg_RMSE += self.RMSE(self.curr_chunk, rec_curr_chunk)

        # Time to show our results !
        if end:
            print(f"\nLa media del ratio de compresión con {self.filters[self.selected_filter]} es de {self.average_c_ratio/self.chunk_index}"
                f" y el RMSE medio es {self.avg_RMSE/self.chunk_index}\n")
            # We reset all of the values
            self.chunk_index = 0
            self.average_c_ratio = 0.0
            self.avg_RMSE = 0.0
            self.selected_filter += 1
            
            # Have we reached the limit ? If so
            # we stop bencharmking
            if self.selected_filter >= len(self.filters):
                print("Hemos acabado de tomar medidas.")
                self.benchmark = False
            else:
                self.wavelet = pywt.Wavelet(self.filters[self.selected_filter])
        
        packed_chunk = struct.pack("!HH", chunk_number, len(compressed_chunk)) + compressed_chunk
        return packed_chunk

    def unpack(self, packed_chunk, dtype=SAMPLE_TYPE):
        (chunk_number, len_compressed_chunk) = struct.unpack("!HH", packed_chunk[:4])
        
        compressed_chunk = packed_chunk[4:]
        decompressed_chunk = zlib.decompress(compressed_chunk)
        # At this stage we still treat the values as 'floats' since
        # we have yet to reconstruct them with our wavelet function
        decompressed_chunk = np.frombuffer(decompressed_chunk, 'float16')

        fpc = ifd.minimal.args.frames_per_chunk

        # Buffer we will use to store the current chunk
        rec_curr_chunk = np.empty((fpc, self.NUMBER_OF_CHANNELS), dtype='int16')

        """
        The format used is the following
        
         +----+-----------+----+----+-----------+----+
         | O1 |     L     | O2 | O1 |     R     | O2 |
         +----+-----------+----+----+-----------+----+

        We ignore O1 & O2 and extract L & R.

        """
        rec_chunk = self.dequantize_and_detransform(decompressed_chunk)

        # Left channel
        rec_curr_chunk[:,0] = rec_chunk[self.n_el_olapped:fpc + self.n_el_olapped]
        # Right channel
        rec_curr_chunk[:,1] = rec_chunk[fpc+(3*self.n_el_olapped):(2*fpc)+(3*self.n_el_olapped)]

        # chunk = self.synthesize(rec_curr_chunk)

        return chunk_number, rec_curr_chunk

    def transform_and_quantize(self, chunk):

        # We have an artificial delay of 1 chunk
        # so we can calculate the lapped transform
        self.prev_chunk[:] = self.curr_chunk
        self.curr_chunk[:] = self.next_chunk
        self.next_chunk[:] = chunk

        # We extract the previous & next overlaps
        prev_overlap = self.prev_chunk[ifd.minimal.args.frames_per_chunk-self.n_el_olapped:]
        next_overlap = self.next_chunk[:self.n_el_olapped]

        # Combine the overlaps with the current chunk
        extended_chunk = np.concatenate((prev_overlap, self.curr_chunk, next_overlap), axis=0)

        # List to store all of the NumPy arrays generated by pywt.wavedec
        decomposition = []

        for c in range(self.NUMBER_OF_CHANNELS):
            tmp = pywt.wavedec(extended_chunk[:,c], wavelet=self.wavelet, level=self.levels, mode=self.signal_mode_ext)
            decomposition += tmp # We append the arrays to the list

        # We have a list of NumPy arrays and
        # we concatenate all of them into a
        # single array
        chunk = np.concatenate(decomposition)
        
        chunk = self.quantize(chunk, dtype='float16')
        
        return chunk
    
    def dequantize_and_detransform(self, decomposition):

        # We invert the process seen in transform_and_quantize

        dec_len = len(decomposition) // 2

        # Buffer to store the reconstructed data
        chunk = np.empty((len(decomposition),), dtype='int16')

        # Reconstruct the data for each channel
        for c in range(self.NUMBER_OF_CHANNELS):

            dec_list = []
            inicio = ceil(dec_len / 2)
            fin = dec_len

            offset = c * dec_len

            # In this loop we extract the data
            # from the array in the correct order
            # e.g. if original size was 1024 and
            # level is 3, then there will be
            # 4 arrays of the following sizes:
            # 512, 256, 128 and 128.
            for x in range(self.levels, 0, -1):
                dec_list.append(self.dequantize(decomposition[inicio+offset:fin+offset], dtype='float32'))
                fin = inicio
                inicio -= ceil(inicio / 2)
            
            # We append the arrays to the list
            dec_list.append(self.dequantize(decomposition[0+offset:fin+offset], dtype='float32'))
            # Reverse the list
            dec_list.reverse()

            # We recover the original data
            chunk[c * dec_len : (c+1) * dec_len] = pywt.waverec(dec_list, wavelet=self.wavelet, mode=self.signal_mode_ext)
        
        return chunk

    def average_energy(self, x):
        return np.sum(x.astype(np.double)*x.astype(np.double))/len(x)
    
    def RMSE(self, x, y):
        error_signal = x - y
        return sqrt(self.average_energy(error_signal))


if __name__ == "__main__":
    ifd.minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(ifd.parser)
    except Exception:
        print("argcomplete not working :-/")
    
    ifd.minimal.args = ifd.minimal.parser.parse_known_args()[0]

    intercom = Temporal_decorrelation()

    try:
        intercom.run()
    except KeyboardInterrupt:
        ifd.parser.exit("\nInterrupted by user")
