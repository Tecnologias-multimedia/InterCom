#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (removes intra-channel redundancy with a DWT (Discrete Wavelet Transform)). '''

import numpy as np
import pywt  # pip install pywavelets
import math
import minimal
import logging

from stereo_MST_coding_32 import Stereo_MST_Coding_32 as Stereo_Coding

from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT
from temporal_no_overlapped_DWT_coding import Temporal_No_Overlapped_DWT__verbose


class Temporal_Overlapped_DWT(Temporal_No_Overlapped_DWT):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

        self.number_of_overlapped_samples = self.max_filters_length * (1 << self.dwt_levels)

        # Structure to keep chunks during encoding
        self.e_chunk_list = []
        self.e_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.e_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.e_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))

        # Structure to keep chunks during decoding
        self.d_chunk_list = []
        self.d_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.d_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))
        self.d_chunk_list.append(np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32))

        # Extended slices
        zero_array = np.zeros(shape=minimal.args.frames_per_chunk+2*self.number_of_overlapped_samples)
        coeffs = pywt.wavedec(zero_array, wavelet=self.wavelet, level=self.dwt_levels, mode="per")
        self.extended_slices = pywt.coeffs_to_array(coeffs)[1]

        logging.info(f"number of overlapped samples = {self.number_of_overlapped_samples}")
        logging.info(f"extended chunk size = {minimal.args.frames_per_chunk+self.number_of_overlapped_samples*2}")


    def analyze(self, chunk):
        fpc = minimal.args.frames_per_chunk
        o = self.number_of_overlapped_samples

        # Input C_i+1
        self.e_chunk_list[2] = Stereo_Coding.analyze(self,chunk)

        # Build extended chunk
        extended_chunk = np.concatenate([self.e_chunk_list[0][-o : ], self.e_chunk_list[1], self.e_chunk_list[2][ : o]])

        # Compute extended decomposition
        extended_DWT_chunk = self.extended_DWT_encode(extended_chunk)

        # Decomposition subset
        decomp_subset = np.zeros((0, minimal.args.number_of_channels), dtype=np.int32)
        decomp_subset = np.concatenate(( decomp_subset, extended_DWT_chunk[self.extended_slices[0][0]] [o//2**self.dwt_levels : -o//2**self.dwt_levels] ))
        for i in range(self.dwt_levels):
            decomp_subset = np.concatenate(( decomp_subset, extended_DWT_chunk[self.extended_slices[i+1]['d'][0]] [o//2**(self.dwt_levels - i) : -o//2**(self.dwt_levels - i)] ))

        # C_i-1 <-- C_i
        self.e_chunk_list[0] = self.e_chunk_list[1]
        # C_i <-- C_i+1
        self.e_chunk_list[1] = self.e_chunk_list[2]

        return decomp_subset

    def extended_DWT_encode(self, chunk):
        DWT_chunk = np.empty((minimal.args.frames_per_chunk + 2*self.number_of_overlapped_samples, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.wavedec(chunk[:, c], wavelet=self.wavelet, level=self.dwt_levels, mode="per")
            channel_DWT_chunk = pywt.coeffs_to_array(channel_coeffs)[0]
            DWT_chunk[:, c] = channel_DWT_chunk
        return DWT_chunk


    # Uses overlapping
    def synthesize(self, chunk_DWT):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk

        # Input D_i+1
        self.d_chunk_list[2] = chunk_DWT

        # Build extended decomposition
        extended_DWT_chunk = np.zeros((0, minimal.args.number_of_channels), dtype=np.int32)
        extended_DWT_chunk = np.concatenate(( extended_DWT_chunk, self.d_chunk_list[0] [self.slices[0][0]] [ -o//2**(self.dwt_levels) : ] ))
        extended_DWT_chunk = np.concatenate(( extended_DWT_chunk, self.d_chunk_list[1] [self.slices[0][0]] ))
        extended_DWT_chunk = np.concatenate(( extended_DWT_chunk, self.d_chunk_list[2] [self.slices[0][0]] [ : o//2**(self.dwt_levels) ] ))        
        for i in range(self.dwt_levels):
            extended_DWT_chunk = np.concatenate(( extended_DWT_chunk, self.d_chunk_list[0] [self.slices[i+1]['d'][0]] [ -o//2**(self.dwt_levels - i) : ] ))
            extended_DWT_chunk = np.concatenate(( extended_DWT_chunk, self.d_chunk_list[1] [self.slices[i+1]['d'][0]] ))
            extended_DWT_chunk = np.concatenate(( extended_DWT_chunk, self.d_chunk_list[2] [self.slices[i+1]['d'][0]] [ : o//2**(self.dwt_levels - i) ] ))

        # Compute extended chunk
        extended_chunk = self.extended_DWT_decode(extended_DWT_chunk)

        # D_i-1 <-- D_i
        self.d_chunk_list[0] = self.d_chunk_list[1]
        # D_i <-- D_i+1
        self.d_chunk_list[1] = self.d_chunk_list[2]

        return Stereo_Coding.synthesize(self,extended_chunk[o:o+fpc])

    def extended_DWT_decode(self, chunk_DWT):
        chunk = np.empty((minimal.args.frames_per_chunk + 2*self.number_of_overlapped_samples, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.extended_slices, output_format="wavedec")
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        return chunk


    '''
    # Ignores overlapping
    def synthesize(self, chunk_DWT):
        chunk = np.empty((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.array_to_coeffs(chunk_DWT[:, c], self.slices, output_format="wavedec")
            chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        chunk = Stereo_Coding.synthesize(self,chunk)
        return chunk
    '''


class Temporal_Overlapped_DWT__verbose(Temporal_Overlapped_DWT, Temporal_No_Overlapped_DWT__verbose):

    # Modified so the added chunk delay is taken into account
    def compute(self, indata, outdata):
        # Remember that indata contains the recorded chunk and
        # outdata, the played chunk, but this is only true after
        # running this method.

        self.recorded_chunks_buff[self.chunk_number % self.cells_in_buffer] = indata.copy()
        #recorded_chunk = self.recorded_chunks_buff[(self.chunk_number - self.chunks_to_buffer - 1) % (self.cells_in_buffer)].astype(np.double)
        recorded_chunk = self.recorded_chunks_buff[(self.chunk_number - self.chunks_to_buffer - 3) % (self.cells_in_buffer)].astype(np.double)  # <- Modification
        played_chunk = outdata.astype(np.double)

        if minimal.args.show_samples:
            print("\033[32mbr_control: ", end=''); self.show_indata(recorded_chunk.astype(np.int))
            print("\033[m", end='')
            # Remember that
            # buffer.Buffering__verbose._record_io_and_play shows also
            # indata and outdata.

            print("\033[32mbr_control: ", end=''); self.show_outdata(played_chunk.astype(np.int))
            print("\033[m", end='')

        square_signal = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            square_signal[c] = recorded_chunk[:, c] * recorded_chunk[:, c]
        # Notice that numpy uses the symbol "*" for computing the dot
        # product of two arrays "a" and "b", that basically is the
        # projection of one of the vectors ("a") into the other
        # ("b"). However, when both vectors are the same and identical
        # in shape (np.arange(10).reshape(10,1) and
        # np.arange(10).reshape(1,10) are the same vector, but one is
        # a row matrix and the other is a column matrix) and the
        # contents are the same, the resulting vector is the result of
        # computing the power by 2, which is equivalent to compute
        # "a**2". Moreover, numpy provides the element-wise array
        # multiplication "numpy.multiply(a, b)" that when "a" and "b"
        # are equal, generates the same result. Among all these
        # alternatives, the dot product seems to be the faster one.

        signal_energy = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            signal_energy[c] = np.sum( square_signal[c] )

        # Compute distortions
        error_signal = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            error_signal[c] = recorded_chunk[:, c] - played_chunk[:, c]

        square_error_signal = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            square_error_signal[c] = error_signal[c] * error_signal[c]

        error_energy = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            error_energy[c] = np.sum( square_error_signal[c] )

        RMSE = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            RMSE[c] = math.sqrt( error_energy[c] )
            self.accumulated_RMSE_per_cycle[c] += RMSE[c]

        SNR = [None] * minimal.args.number_of_channels
        for c in range(minimal.args.number_of_channels):
            if error_energy[c].any():
                if signal_energy[c].any():
                    SNR[c] = 10.0 * math.log( signal_energy[c] / error_energy[c] )
                    self.accumulated_SNR_per_cycle[c] += SNR[c]

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
        intercom = Temporal_Overlapped_DWT__verbose()
    else:
        intercom = Temporal_Overlapped_DWT()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
