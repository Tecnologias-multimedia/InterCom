#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Echo cancellation LMS.'''

import logging
import minimal
import buffer
import numpy as np
from adaptfilt import nlms

class Echo_Cancellation(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def cancel_echo_old(self, microphone_signal, speaker_signal):
        M = 256
        step = 0.000001
        y = np.zeros((1024-M+1,2))
        e = np.zeros((1024-M+1,2))

        for i in range(microphone_signal.shape[1]):
            y[:, i], e[:, i], w = nlms(speaker_signal[:, i], microphone_signal[:, i], M, step)

        return e
        
    def cancel_echo_old(self, microphone_signal, speaker_signal):
        M = 256
        step = 0.000001
        y = np.zeros((1024-M+1,2))
        e = np.zeros((1024-M+1,2))
        #print(np.max(microphone_signal))
        print(np.max(speaker_signal))

        for i in range(microphone_signal.shape[1]):
            y[:, i], e[:, i], w = nlms(speaker_signal[:, i].astype(np.float32), microphone_signal[:, i].astype(np.float32), M, step)

        return y
        
    def cancel_echo_old(self, microphone_signal, speaker_signal):
        M = 256
        step = 0.1
        padding = np.zeros((M-1, 2))
        padded_SP = np.vstack([padding, speaker_signal])
        padded_MS = np.vstack([padding, microphone_signal])
        y = np.zeros((1024,2))
        e = np.zeros((1024,2))
        #print(np.max(microphone_signal))
        #print(np.max(speaker_signal))

        for i in range(microphone_signal.shape[1]):
            y[:, i], e[:, i], w = nlms(padded_SP[:, i], padded_MS[:, i], M, step)

        return y

    def cancel_echo(self, microphone_signal, speaker_signal):
        M = 128
        step = 0.1
        padding = np.zeros((M-1, 2))
        padded_SP = np.vstack([padding, speaker_signal.copy()])
        padded_MS = np.vstack([padding, microphone_signal.copy()])
        y = np.zeros((1024,2))
        e = np.zeros((1024,2))
        #print(np.max(microphone_signal))
        #print(np.max(speaker_signal))

        for i in range(2):
            y[:, i], e[:, i], w = nlms(padded_SP[:, i].astype(np.float32), padded_MS[:, i].astype(np.float32), M, step)

        print(np.max(y))
        y = np.clip(y, -32768, 32767)
        return y.astype(np.int16)

    def _record_IO_and_play_old(self, indata, outdata, frames, time, status):
        echo_signal = self.cancel_echo(indata, outdata)
        padding = np.zeros((1024 - echo_signal.shape[0], 2))
        echo_signal = np.vstack([echo_signal, padding])

        indata[:] = echo_signal
        super()._record_IO_and_play(indata, outdata, frames, time, status)

    def _record_IO_and_play_old(self, indata, outdata, frames, time, status):
        ECS = self.cancel_echo(indata, outdata)
        #print(np.max(ECS))
        padding = np.zeros((1024 - ECS.shape[0], 2))
        ECS = np.vstack([ECS, padding])
        #indata[:] = ECS
        super()._record_IO_and_play(indata, outdata, frames, time, status)

    def _record_IO_and_play(self, indata, outdata, frames, time, status):
        ECS = self.cancel_echo(indata.copy(), outdata.copy())
        #indata[:] = ECS
        #indata[:] = indata
        #super()._record_IO_and_play(indata, outdata, frames, time, status)

class Echo_Cancellation__verbose(Echo_Cancellation, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()


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
        intercom = Echo_Cancellation__verbose()
    else:
        intercom = Echo_Cancellation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
