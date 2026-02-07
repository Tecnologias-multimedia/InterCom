#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Overlapping chunks (DWT).'''

# Nomenclature:
#
# chunk = the sequence of samples returned by the sound card
# decomposition = the sequence of coefficients returned by the DWT(chunk)
# extended_chunk = [last samples prev chunk, chunk, first samples next chunk]
# extended_decomposition = the output of DWT(extended_chunk)

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

        self.number_of_overlapped_samples = self.max_filters_length * (1 << self.DWT_levels)
        logging.info(f"number of overlapped samples = {self.number_of_overlapped_samples}")
        logging.info(f"extended chunk size = {minimal.args.frames_per_chunk + self.number_of_overlapped_samples*2}")

        self.chunk_list = [np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32) for _ in range(3)]
        self.decom_list = [np.zeros((minimal.args.frames_per_chunk, minimal.args.number_of_channels), dtype=np.int32) for _ in range(3)]
        
        extended_chunk = np.zeros(
            shape=minimal.args.frames_per_chunk + 2*self.number_of_overlapped_samples)
        coeffs = pywt.wavedec(
            extended_chunk,
            wavelet=self.wavelet,
            level=self.DWT_levels,
            mode="per")
        self.extended_slices = pywt.coeffs_to_array(coeffs)[1]

    def get_extended_chunk(self):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk

        extended_chunk = np.concatenate(
            (self.chunk_list[0][-o:],
             self.chunk_list[1],
             self.chunk_list[2][:o])
        )
        
        return extended_chunk

    def get_chunk(self, extended_chunk):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk
        chunk = extended_chunk[o:o+fpc]
        return chunk
    
    def get_decomposition(self, extended_decomposition):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk
        decomposition = extended_decomposition[self.extended_slices[0][0]][o//2**self.DWT_levels:-o//2**self.DWT_levels]
        for l in range(self.DWT_levels):
            decomposition = np.concatenate(
                (decomposition,
                 extended_decomposition[self.extended_slices[l+1]['d'][0]][o//2**(self.DWT_levels - l):-o//2**(self.DWT_levels - l)])
            )
        return decomposition

    def get_extended_decomposition(self):
        o = self.number_of_overlapped_samples
        fpc = minimal.args.frames_per_chunk

        # Build the extended decomposition
        DWT_extended_chunk = np.zeros((0, minimal.args.number_of_channels), dtype=np.int32)
        DWT_extended_chunk = np.concatenate(( DWT_extended_chunk, self.decom_list[0] [self.slices[0][0]] [ -o//2**(self.DWT_levels) : ] ))
        DWT_extended_chunk = np.concatenate(( DWT_extended_chunk, self.decom_list[1] [self.slices[0][0]] ))
        DWT_extended_chunk = np.concatenate(( DWT_extended_chunk, self.decom_list[2] [self.slices[0][0]] [ : o//2**(self.DWT_levels) ] ))        
        for i in range(self.DWT_levels):
            DWT_extended_chunk = np.concatenate(( DWT_extended_chunk, self.decom_list[0] [self.slices[i+1]['d'][0]] [ -o//2**(self.DWT_levels - i) : ] ))
            DWT_extended_chunk = np.concatenate(( DWT_extended_chunk, self.decom_list[1] [self.slices[i+1]['d'][0]] ))
            DWT_extended_chunk = np.concatenate(( DWT_extended_chunk, self.decom_list[2] [self.slices[i+1]['d'][0]] [ : o//2**(self.DWT_levels - i) ] ))
        return DWT_extended_chunk
        
    def stereo_IDWT(self, DWT_extended_chunk):
        extended_chunk = np.empty_like(DWT_extended_chunk)
        for c in range(minimal.args.number_of_channels):
            channel_coeffs = pywt.array_to_coeffs(DWT_extended_chunk[:, c], self.extended_slices, output_format="wavedec")
            extended_chunk[:, c] = pywt.waverec(channel_coeffs, wavelet=self.wavelet, mode="per")
        return extended_chunk

    def analyze(self, chunk):
        self.chunk_list[0] = self.chunk_list[1]  # C_i-1 <-- C_i
        self.chunk_list[1] = self.chunk_list[2]  # C_i <-- C_i+1
        self.chunk_list[2] = chunk  # Input C_i+1
        extended_chunk = self.get_extended_chunk()
        extended_decomposition = Temporal_No_Overlapped_DWT.analyze(self, extended_chunk)
        decomposition = self.get_decomposition(extended_decomposition)
        return decomposition

    def synthesize(self, decomposition):
        self.decom_list[0] = self.decom_list[1]  # ED_i-1 <-- ED_i
        self.decom_list[1] = self.decom_list[2]  # ED_i <-- ED_i+1
        self.decom_list[2] = decomposition  # Input ED_i+1
        extended_decomposition = self.get_extended_decomposition()        
        extended_chunk = Temporal_No_Overlapped_DWT.synthesize(self, extended_decomposition)
        chunk = self.get_chunk(extended_chunk)
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
            # buffer.Buffering__verbose._record_IO_and_play shows also
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
    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = Temporal_Overlapped_DWT__verbose()
    else:
        intercom = Temporal_Overlapped_DWT()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
