#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Simple echo cancellation. Substract an attenuated version of the last chunk that has been played from the last recorded chunk, delaying the played chunk the propagation time from the speaker to the mic. Substract to the played chunk an attenuated version of the chunk that was sent to the interlocutor "buffering_time" ms before.'''

import numpy as np
import struct
import math
import logging

#import pygame_widgets
import pygame
from pygame_widgets.slider import Slider
from pygame_widgets.textbox import TextBox

import minimal
import buffer
#import queue

import threading

from scipy import signal
import tkinter as tk
#from tkinter import ttk

class Delay_Slider():
    def __init__(self, root):
        self.root = root
        self.root.title('Sine Wave with Slider')

        # Set up initial parameters
        self.delay = tk.IntVar(value=10)

        # Create UI elements
        #self.create_widgets()
        self.delay_slider = ttk.Scale(self.root, from_=0.1, to=5.0, length=200, orient=tk.HORIZONTAL, variable=self.delay, command=self.refresh)


    def refresh(self, event=None):
        delay = self.delay.get()

        # Update the label text
        self.amplitude_label.config(text=f"Delay: {delay}")

        # Update the canvas with the new signal
        self.canvas.delete('all')
        
class Echo_Cancellation(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.delay = 20 # In frames
        self.attenuation = 0.5
        #self.sent_chunks = queue.Queue()
        #for i in range(self.chunks_to_buffer):
        #    self.sent_chunks.put(self.zero_chunk)
        self.last_played_chunk = self.zero_chunk

    def __record_io_and_play(self, indata, outdata, frames, time, status):
        super()._record_io_and_play(indata, outdata, frames, time, status)
        self.recorded_chunk = outdata

    def __record_io_and_play(self, recorded_chunk, played_chunk, frames, time, status):
        super()._record_io_and_play(recorded_chunk, played_chunk, frames, time, status)
        
class Echo_Cancellation__verbose(Echo_Cancellation, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()
        #self.window_heigh = 512
        #self.screen = pygame.display.set_mode((minimal.args.frames_per_chunk, self.window_heigh))
        #self.eye = 255*np.eye(minimal.args.frames_per_chunk, dtype=int)
        self.corr_data = self.generate_zero_chunk()[:, 0]

        self.recorded_chunk = self.generate_zero_chunk()

        self.window_heigh = 1024
        self.display = pygame.display.set_mode((minimal.args.frames_per_chunk, self.window_heigh))
        self.display.fill((0, 0, 0))
        self.chunk_surface = pygame.surface.Surface((minimal.args.frames_per_chunk, 1024)).convert()
        self.chunk_eye = 255*np.eye(minimal.args.frames_per_chunk, dtype=int)
        self.chunk_in_graphics = np.zeros((1024, minimal.args.frames_per_chunk, 3), dtype=np.uint8)

        #input_delay_thread = threading.Thread(target=self.loop_input_delay)
        #input_delay_thread.daemon = True
        #input_delay_thread.start()

        #self.root = tk.Tk()
        #app = Delay_Slider(self.root)
        #self.root.mainloop()

        self.slider = Slider(self.display, 100, 100, 800, 40, min=0, max=1023, step=1, initial=0)
        self.output = TextBox(self.display, x=0, y=200, width=75, height=50, fontSize=30)
        self.output.disable()  # Act as label instead of textbox
    
    def loop_input_delay(self):
        #while True:
        #    self.delay = int(input("delay:"))
        #    print(self.delay)
        print("*"*40)
        
    def update_display(self):
        x = self.chunk_eye[800 - np.clip(self.recorded_chunk[:, 0]//64, -128, 128)]
        self.chunk_in_graphics[:, :, 0] = x
        surface = pygame.surfarray.make_surface(self.chunk_in_graphics)
        x = self.chunk_eye[800 - np.clip(self.last_played_chunk[:, 0]//64, -128, 128)]
        self.chunk_in_graphics[:, :, 1] = x
        surface = pygame.surfarray.make_surface(self.chunk_in_graphics)
        x = self.chunk_eye[800 - np.clip(self.no_echo_chunk[:, 0]//64, -128, 128)]
        self.chunk_in_graphics[:, :, 2] = x
        surface = pygame.surfarray.make_surface(self.chunk_in_graphics)
        #surf = pygame.surfarray.blit_array(self.surface, self.recorded_chunk[:,0])
        #for i in range(256):
        #    self.display.set_at((i, self.recorded_chunk[i][0] + 128), (255, 0, 0))
        #    self.display.set_at((i, self.recorded_chunk[i][1] + 128), (0, 0, 255))
        self.display.blit(surface, (0, 0))
        self.delay = self.slider.getValue()
        self.output.setText(self.delay)
        super().update_display()

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
        #a = self.recorded_chunk[:, 1] #chunk[:, 0]
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
            #print(lag)
        #DAC[:] = (chunk - 0.2*self.recorded_chunk).astype(np.int16) #- np.roll(chunk, 0)
        #DAC[:] = (chunk - 0.3*np.roll(self.recorded_chunk,8)).astype(np.int16) #- np.roll(chunk, 0)
        #chunk_without_echo = chunk - (0.5*np.roll(old_sent_chunk, -0)).astype(np.int16)
        #chunk_without_echo = chunk - (0.99*old_sent_chunk).astype(np.int16)
        #chunk_without_echo = old_sent_chunk
        #chunk_without_echo = chunk
        #print(chunk, old_sent_chunk)
        #DAC[:] = chunk_without_echo
        #DAC[:] = self.zero_chunk
        print(self.delay, end=' ')
        DAC[:] = chunk
        self.last_played_chunk = chunk

    def pack(self, chunk_number, last_recorded_chunk):
        #chunk = chunk - np.roll(self.recorded_chunk, -4)
        #chunk = chunk - (0.9*np.roll(self.recorded_chunk, 24)).astype(np.int16)
        #print(self.recorded_chunk)
        #print(chunk)
        #print(last_recorded_chunk)
        self.no_echo_chunk = last_recorded_chunk.astype(np.int32) - (self.attenuation*np.roll(self.last_played_chunk, self.delay)).astype(np.int32)
        self.no_echo_chunk = self.no_echo_chunk.astype(np.int16)
        #print(last_recorded_chunk)

        packed_chunk = super().pack(chunk_number, self.no_echo_chunk)
        #packed_chunk = super().pack(chunk_number, last_recorded_chunk)
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
