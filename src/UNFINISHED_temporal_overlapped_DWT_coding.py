#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (removes intra-channel redundancy with a DWT (Discrete Wavelet Transform)). '''

import numpy as np
import sounddevice as sd
import pywt
import math
import time
import minimal
import compress
from compress import Compression as Compression
import br_control
from br_control import BR_Control as BR_Control 
import stereo_MST_coding
from stereo_coding import Stereo_Coding as Stereo_Coding
from stereo_coding import Stereo_Coding__verbose as Stereo_Coding__verbose
import temporal_coding
from temporal_coding import Temporal_Coding as Temporal_Coding
from temporal_coding import Temporal_Coding__verbose as Temporal_Coding__verbose

class Chunks_Overlapping(Temporal_Coding):
    
    def __init__(self):
        super().__init__()
        #self.prev_chunk = self.zero_chunk
        #self.curr_chunk = None
        #self.next_chunk = None
        self.prev_chunk = super().generate_zero_chunk()
        #self.last_samples = np.zeros((self.nos, 2))
        overlaped_area_size = self.max_filters_length * (1 << self.dwt_levels)
        self.overlaped_area_size = 1<<math.ceil(math.log(overlaped_area_size)/math.log(2))
        #self.overlaped_area_size = 0
        if __debug__:
            print("overlaped_area_size =", self.overlaped_area_size)

        # Structure used during the decoding
        zero_array = np.zeros(shape=minimal.args.frames_per_chunk + self.overlaped_area_size)
        coeffs = pywt.wavedec(zero_array, wavelet=self.wavelet, level=self.dwt_levels, mode="per")
        self.slices = pywt.coeffs_to_array(coeffs)[1]

    def analyze(self, chunk):
        DWT_chunk = np.empty((minimal.args.frames_per_chunk+self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        print("B", DWT_chunk.shape)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk

    def synthesize(self, chunk_DWT):
        '''Inverse DWT.'''
        chunk = np.empty((minimal.args.frames_per_chunk+self.overlaped_area_size, self.NUMBER_OF_CHANNELS), dtype=np.int32)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        return chunk

    # Use the last samples of the previous chunk to build a left-shifted extended chunk, whose left DWT coefficients should not be transmitted. For the chunk number 0, these last samples are zero. In the decoder, the discarded coefficients should be replaced by the last coefficients of the previous chunk. Only the non-overlapped samples should be played. In this version, all the coefficients are transmitted.
    def pack(self, chunk_number, chunk):
        # Recuerda: la redundancia espacial podría estar ya eliminada
        #extended_chunk = np.concatenate([self.prev_chunk[:-nos], chunk, self.next_chunk[:nos]])
        extended_chunk = np.concatenate([self.prev_chunk[-self.overlaped_area_size:], chunk])
        print("A", chunk.shape, self.prev_chunk[-self.overlaped_area_size:].shape, extended_chunk.shape)
        self.prev_chunk = chunk        
        extended_chunk = Stereo_Coding.analyze(self, extended_chunk)
        extended_chunk = self.analyze(extended_chunk)
        quantized_chunk = BR_Control.quantize(self, extended_chunk)
        compressed_chunk = Compression.pack(self, chunk_number, quantized_chunk)
        return compressed_chunk

    def unpack(self, compressed_chunk):
        chunk_number, quantized_chunk = Compression.unpack(self, compressed_chunk)
        chunk = BR_Control.dequantize(self, quantized_chunk)
        chunk = chunk.reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS).astype(np.int32)
        chunk = self.synthesize(chunk)[self.overlaped_area_size:]
        chunk = Stereo_Coding.synthesize(self, chunk)
        self.prev_chunk = chunk
        return chunk_number, chunk

    def _record_send_and_play(self, indata, outdata, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        packed_chunk = self.pack(self.chunk_number, self.prev_chunk)
        self.prev_chunk = self.curr_chunk
        self.curr_chunk = indata
        self.send(packed_chunk)
        chunk = self.unbuffer_next_chunk()
        self.play_chunk(outdata, chunk)

    def _analyze(self, extended_chunk):
        return super.analyze(extended_chunk)
    
    def _synthesize(self, chunk_DWT):
        ''' Restores the original representation of the chunk.

        Parameters
        ----------
        chunk_DWT : numpy.ndarray
            The chunk to restore.

        Returns
        -------
        numpy.ndarray
            The restored chunk.
        '''
        chunk = np.empty((minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS), dtype=self.SAMPLE_TYPE)
        for c in range(self.NUMBER_OF_CHANNELS):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            chunk[:, c] = np.rint(pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")).astype(self.SAMPLE_TYPE)
        return chunk


class Chunks_Overlapping__verbose(Chunks_Overlapping, Temporal_Coding__verbose):
    pass

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Chunks_Overlapping__verbose()
    else:
        intercom = Chunks_Overlapping()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
