#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (removes intra-channel redundancy with a DWT (Discrete Wavelet Transform)). '''

import numpy as np
import sounddevice as sd
import pywt
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")
import time
import minimal
import compress
from compress import Compression as Compression
import br_control
from br_control import BR_Control as BR_Control 
import stereo_coding
from stereo_coding import Stereo_Coding as Stereo_Coding
from stereo_coding import Stereo_Coding__verbose as Stereo_Coding__verbose
import temporal_coding
from temporal_coding import Temporal_Coding as Temporal_Coding
from temporal_coding import Temporal_Coding__verbose as Temporal_Coding__verbose

class Chunks_Overlapping(Temporal_Coding):
    
    def __init__(self):
        super().__init__()
        print("Overlapping chunks")
        self.nos = 10
        print("Number of overlapped samples =", self.nos)
        #self.prev_chunk = self.zero_chunk
        #self.curr_chunk = None
        #self.next_chunk = None
        self.last_samples = np.zeros((self.nos, 2))

    def _record_send_and_play(self, indata, outdata, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        packed_chunk = self.pack(self.chunk_number, self.prev_chunk)
        self.prev_chunk = self.curr_chunk
        self.curr_chunk = indata
        self.send(packed_chunk)
        chunk = self.unbuffer_next_chunk()
        self.play_chunk(outdata, chunk)

    def _pack(self, chunk_number, chunk):
        # Recuerda: la redundancia espacial podría estar ya eliminada
        extended_chunk = np.concatenate([self.prev_chunk[:-nos], chunk, self.next_chunk[:nos]])
        self.next_chunk = chunk
        
        ''' I/O idem to Stereo_Coding.pack(). Redefines it to provide intra-channel redundancy removal. '''
        Stereo_Coding.analyze(self, chunk)
        chunk = chunk.astype(self.COEFFICIENT_TYPE)
        chunk = self.analyze(chunk)
        quantized_chunk = BR_Control.quantize(self, chunk, self.COEFFICIENT_TYPE)
        compressed_chunk = Compression.pack(self, chunk_number, quantized_chunk)
        return compressed_chunk

    def _unpack(self, compressed_chunk):
        ''' I/O idem to IFD.unpack(). Redefines it to restore the original chunk representation. '''
        chunk_number, quantized_chunk = Compression.unpack(self, compressed_chunk, self.COEFFICIENT_TYPE)
        chunk = BR_Control.dequantize(self, quantized_chunk, self.COEFFICIENT_TYPE)
        chunk = self.synthesize(chunk)
        chunk = chunk.astype(minimal.Minimal.SAMPLE_TYPE)
        Stereo_Coding.synthesize(self, chunk)
        return chunk_number, chunk

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

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Chunks_Overlapping__verbose()
    else:
        intercom = Chunks_Overlapping()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
