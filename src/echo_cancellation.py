#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Simple echo cancellation. Substract an attenuated version of the last chunk that has been played from the last recorded chunk, delaying the played chunk the propagation time from the speaker to the mic. Substract to the played chunk an attenuated version of the chunk that was sent to the interlocutor "buffering_time" ms before.'''

import numpy as np
import struct
import math
import logging

import pygame

import minimal
import buffer
import queue

from scipy import signal

class Echo_Cancellation(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.delay = 500 # In frames
        self.attenuation = 0.2
        #self.sent_chunks = queue.Queue()
        #for i in range(self.chunks_to_buffer):
        #    self.sent_chunks.put(self.zero_chunk)ç
        self.last_played_chunk = self.zero_chunk

    def __record_io_and_play(self, indata, outdata, frames, time, status):
        super()._record_io_and_play(indata, outdata, frames, time, status)
        self.audio_data = outdata

    def __record_io_and_play(self, recorded_chunk, played_chunk, frames, time, status):
        super()._record_io_and_play(recorded_chunk, played_chunk, frames, time, status)
        
class Echo_Cancellation__verbose(Echo_Cancellation, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()
        #self.window_heigh = 512
        #self.screen = pygame.display.set_mode((minimal.args.frames_per_chunk, self.window_heigh))
        #self.eye = 255*np.eye(minimal.args.frames_per_chunk, dtype=int)
        self.corr_data = self.generate_zero_chunk()[:, 0]

        self.audio_data = self.generate_zero_chunk()

    def update_plot(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
                break

        matrix = self.eye[self.corr_data]
        #print(matrix.shape)
        surface = pygame.surfarray.make_surface(matrix)
        self.screen.blit(surface, (0, 0))
        pygame.display.update()
        #super().update_plot()

    def _get_correlation(self, a, v):
        mean_a = np.mean(a)
        var_a = np.var(a)
        na = a - mean_a
        mean_v = np.mean(v)
        var_v = np.var(v)
        nv = v - mean_v
        corr = np.correlate(a=na, v=nv, mode='full')[len(na)-1:]
        corr = corr / (var_v+1) / len(na)
        return corr

    def normalize(self, x):
        _max = np.max(x).astype(np.float32)
        _min = np.min(x).astype(np.float32)
        nx = (x - _min)/(_max - _min)
        return nx

    def get_correlation(self, in1, in2):
        
        corr = signal.correlate(self.normalize(in1), self.normalize(in2), mode="full")
        #_max = np.max(corr).astype(np.float32)
        #_min = np.min(corr).astype(np.float32)
        #print(_max, _min)
        #ncorr = (corr - _min)/(_max - _min)
        #ncorr = corr / 32768
        #print(np.max(ncorr), np.min(ncorr))
        #mean = np.mean(in1)
        #var = np.var(in1)
        #corr = corr / (var) / len(in1)
        return corr
        
    def play_chunk(self, DAC, chunk):
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        chunk = chunk.reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        a = chunk[:, 1]
        #a = self.audio_data[:, 1] #chunk[:, 0]
        #old_sent_chunk = self.sent_chunks.get()
        #v = old_sent_chunk[:, 1]
        v = self._buffer[(self.played_chunk_number - 2) % self.cells_in_buffer].reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)[:, 1]
        #v = a
        #v = np.concatenate([0.5*a[:100].astype(np.int16), a])
        #print(len(v))
        if np.max(a) > 0 and np.max(v) > 0:
            correlation = self.get_correlation(a, v)
            #max_index = np.argmax(ncorr)
            #max_val = ncorr[max_index]
            #print(np.max(ncorr), np.min(ncorr))
            #self.corr_data = (256*ncorr + 256).astype(np.uint32)
            self.corr_data = correlation.astype(np.uint32)
            lags = signal.correlation_lags(a.size, v.size, mode="full")
            lag = lags[np.argmax(correlation[0:])]
            print(lag)
        #DAC[:] = (chunk - 0.2*self.audio_data).astype(np.int16) #- np.roll(chunk, 0)
        #DAC[:] = (chunk - 0.3*np.roll(self.audio_data,8)).astype(np.int16) #- np.roll(chunk, 0)
        #chunk_without_echo = chunk - (0.5*np.roll(old_sent_chunk, -0)).astype(np.int16)
        #chunk_without_echo = chunk - (0.99*old_sent_chunk).astype(np.int16)
        #chunk_without_echo = old_sent_chunk
        #chunk_without_echo = chunk
        #print(chunk, old_sent_chunk)
        #DAC[:] = chunk_without_echo
        #DAC[:] = self.zero_chunk
        DAC[:] = chunk
        self.last_played_chunk = chunk

    def pack(self, chunk_number, last_recorded_chunk):
        #chunk = chunk - np.roll(self.audio_data, -4)
        #chunk = chunk - (0.9*np.roll(self.audio_data, 24)).astype(np.int16)
        #print(self.audio_data)
        #print(chunk)
        #print(last_recorded_chunk)
        last_recorded_chunk = last_recorded_chunk - (0.5*np.roll(self.last_played_chunk, 8)).astype(np.int16)
        #print(last_recorded_chunk)

        packed_chunk = super().pack(chunk_number, last_recorded_chunk)
        #self.sent_chunks.put(recorded_chunk)
        return packed_chunk

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
        intercom = Echo_Cancellation__verbose()
    else:
        intercom = Echo_Cancellation()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
       intercom.print_final_averages()
