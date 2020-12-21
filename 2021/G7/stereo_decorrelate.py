#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator. Decorrelation version

    Decorrelation allows to remove redundancy between channels.
    This process helps to improve the ratio compresion, especially
    if mono microphone is used.
'''

import numpy as np
import math
import threading
import time
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

# Import previous milestones
import minimal
import buffer
import compress
import br_control

# Used to generate files with statistical data
import os

class Stereo_decorrelation(br_control.BR_Control):
    """ Stereo_decorrelation allows to separate channels
    into bands of "frequencies". The existent redundancy
    between channels is suppressed to enhance compression
    """

    def __init__(self):
        """
        Initializes the instance. Basically generate buffers to
        avoid array consruction each time a chunk is sent
        or received
        """
        super().__init__()
        self.analyze_buffer = np.zeros([minimal.args.frames_per_chunk, minimal.Minimal.NUMBER_OF_CHANNELS], dtype=np.int32)
        self.synthesize_buffer = np.zeros([minimal.args.frames_per_chunk, minimal.Minimal.NUMBER_OF_CHANNELS], dtype=np.int16)
        #self.subbands = np.zeros(minimal.CHANNELS)

    def MST_analyze(self, x):
        """
        Analyze method separates channels into subbands using MST
        This method has been provided
        """
        w = np.empty_like(x, dtype=np.int32)
        w[:, 0] = x[:, 0].astype(np.int32) + x[:, 1]  # L(ow frequency subband)
        w[:, 1] = x[:, 0].astype(np.int32) - x[:, 1]  # H(igh frequency subband)
        return w

    def MST_synthesize(self, w):
        """
        Synthesize method reconstruct channels using the subbands
        This method has been provided
        """
        x = np.empty_like(w, dtype=np.int16)
        x[:, 0] = (w[:, 0] + w[:, 1]) / 2  # L(ow frequency subband)
        x[:, 1] = (w[:, 0] - w[:, 1]) / 2  # H(igh frequency subband)
        return x

    def pack(self, chunk_number, chunk):
        '''Overrides pack method from BR_Control
        Tries to enhance speed avoiding call another method and using
        a buffer.
        '''
        self.analyze_buffer[:, 0] = chunk[:, 0].astype(np.int32) + chunk[:, 1]
        self.analyze_buffer[:, 1] = chunk[:, 0].astype(np.int32) - chunk[:, 1]

        packed_chunk = super().pack(chunk_number, self.analyze_buffer)
        return packed_chunk

    def unpack(self, packed_chunk, dtype=minimal.Minimal.SAMPLE_TYPE):
        '''Overrides unpack method from BR_Control
        Tries to enhance speed avoiding call another method and using
        a buffer. Applies division using shift operator.
        '''
        chunk_number, chunk = super().unpack(packed_chunk, dtype)
        self.synthesize_buffer[:, 0] = (chunk[:, 0] + chunk[:, 1]) >> 1
        self.synthesize_buffer[:, 1] = (chunk[:, 0] - chunk[:, 1]) >> 1

        return chunk_number, self.synthesize_buffer

class Stereo_decorrelation__verbose(Stereo_decorrelation, br_control.BR_Control__verbose):
    """Verbose class used to show data from Stereo_decorrelation usage.
    A new field called ratio is implemented to show how much compression
    is achieved. This compression is measured via received_kbps / 1411.2
    The number 1411.2 is not a magic number. This is the result of:

        sample_rate * number_of_channels * bits

    In all previous milestones, the values are being:

        44100 * 2 * 16 = 1411200 => 1411.2 kbps
    """
    def __init__(self):
        super().__init__()
        self.compression_ratio = 0

    def stats(self):
        string = super().stats()
        string += "{:>10f}".format(self.compression_ratio)

        return string

    def first_line(self):
        string = super().first_line()
        string += "{:>4s}".format('') # self.quantization_step
        return string

    def second_line(self):
        string = super().second_line()
        string += "{:>6s}".format('Ratio')  # self.quantization_step
        return string

    def separator(self):
        string = super().separator()
        string += f"{'=' * (10)}"
        return string

    def cycle_feedback(self):
        ''' Computes and shows the statistics. '''

        self.average_RMSE_per_cycle = self.accumulated_RMSE_per_cycle / self.chunks_per_cycle
        self.average_RMSE = self.moving_average(self.average_RMSE, self.average_RMSE_per_cycle, self.cycle)

        self.average_SNR_per_cycle = self.accumulated_SNR_per_cycle / self.chunks_per_cycle
        self.average_SNR = self.moving_average(self.average_SNR, self.average_SNR_per_cycle, self.cycle)

        super().cycle_feedback()

        self.accumulated_SNR_per_cycle[:] = 0.0
        self.accumulated_RMSE_per_cycle[:] = 0.0

        self.compression_ratio = self.received_kbps / 1411.2
        # os.system("echo " + str(self.compression_ratio) + " >> file") Used to store data in file

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_args()
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Stereo_decorrelation__verbose()
    else:
        intercom = Stereo_decorrelation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")