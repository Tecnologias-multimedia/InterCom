#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Echo cancellation. Substract an attenuated and delayed verion of the last recorded chunk to the last played chunk. The delayed version of the last recorded chunk takes the last samples of the previously (to the last) recorded chunk.'''

import numpy as np
import struct
import math
import logging
import threading

from scipy import signal
#from tkinter import ttk
#import queue
import pygame
#import pygame_widgets
from pygame_widgets.slider import Slider
from pygame_widgets.textbox import TextBox
import pygame_widgets

import minimal
import buffer

class Echo_Cancellation(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.delay = 128 # In frames
        self.attenuation = 0.5
        self.last_recorded_chunk = self.zero_chunk
        self.prev_recorded_chunk = self.zero_chunk
        
        self.last_sent_chunks = []
        #self.sent_chunks = queue.Queue()
        for i in range(self.chunks_to_buffer+2):
            self.last_sent_chunks.append(self.zero_chunk)
        self.LSC_counter = 0
        self.last_played_chunk = self.zero_chunk
        self.ones = np.ones_like(self.last_played_chunk)
        for i in range(len(self.ones)):
            if i % 2:
                self.ones[i] = -self.ones[i]
        pygame.init()
        self.win = pygame.display.set_mode((1000, 600))

        self.slider = Slider(self.win, 100, 100, 800, 40, min=0, max=self.delay*2, step=1, initial=self.delay)
        self.output = TextBox(self.win, 475, 200, 50, 50, fontSize=30)
        self.slider2 = Slider(self.win, 100, 400, 800, 40, min=0.0, max=2.0, step=0.01, initial=self.attenuation)
        self.output2 = TextBox(self.win, 475, 500, 50, 50, fontSize=30)

        self.output.disable()  # Act as label instead of textbox
        self.output2.disable()  # Act as label instead of textbox

    def run(self):
        logging.info("Press CTRL+c to quit")
        self.played_chunk_number = 0
        with self.stream(self._handler):
            first_received_chunk_number = self.receive_and_buffer()
            logging.debug("first_received_chunk_number =", first_received_chunk_number)
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                self.receive_and_buffer()
                events = pygame.event.get()
                for event in events:
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        run = False
                        quit()

                self.win.fill((255, 255, 255))

                self.output.setText(self.slider.getValue())
                self.output2.setText(self.slider2.getValue())

                self.delay = self.slider.getValue()
                self.attenuation = self.slider2.getValue()
                print(self.delay, self.attenuation)
                pygame_widgets.update(events)
                pygame.display.update()

    def pack(self, chunk_number, last_recorded_chunk):
        self.last_recorded_chunk = last_recorded_chunk
        #self.last_sent_chunks[self.LSC_counter] = last_recorded_chunk
        #chunk = chunk - np.roll(self.recorded_chunk, -4)
        #chunk = chunk - (0.9*np.roll(self.recorded_chunk, 24)).astype(np.int16)
        #print(self.recorded_chunk)
        #print(chunk)
        #print(last_recorded_chunk)
        #print(self.last_played_chunk)
        #chunk_to_substract = (self.attenuation*np.roll(self.last_played_chunk, self.delay)).astype(np.int32)
        #chunk_to_substract = self.attenuation * np.concatenate(self.last_sent_chunks)[self.delay:self.delay+minimal.args.frames_per_chunk]
        chunk_to_substract = self.attenuation * np.concatenate([self.prev_recorded_chunk, self.last_recorded_chunk])[minimal.args.frames_per_chunk - self.delay : 2*minimal.args.frames_per_chunk - self.delay].astype(np.int32)
        #chunk_to_substract *= self.ones
        chunk_to_substract = np.random.rand(len
        #print(chunk_to_substract)
        #self.no_echo_chunk = last_recorded_chunk.astype(np.int32) - chunk_to_substract
        #self.no_echo_chunk = self.last_sent_chunks[self.LSC_counter] - chunk_to_substract
        self.no_echo_chunk = last_recorded_chunk - chunk_to_substract
        
        #self.no_echo_chunk = last_recorded_chunk
        self.no_echo_chunk = self.no_echo_chunk.astype(np.int16)
        #self.no_echo_chunk = self.zero_chunk

        #print(last_recorded_chunk)

        packed_chunk = super().pack(chunk_number, self.no_echo_chunk)
        #packed_chunk = super().pack(chunk_number, last_recorded_chunk)
        #self.sent_chunks.put(recorded_chunk)
        #self.LSC_counter = (self.LSC_counter + 1) % (self.chunks_to_buffer + 1)
        return packed_chunk

    def play_chunk(self, DAC, chunk):
        super().play_chunk(DAC, chunk)
        self.last_played_chunk = chunk.reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        self.chunk_number = (self.chunk_number + 1) % self.CHUNK_NUMBERS
        self.prev_recorded_chunk = self.last_played_chunk
        self.last_recorded_chunk = ADC[:]
        packed_chunk = self.pack(self.chunk_number, ADC)
        self.send(packed_chunk)
        chunk = self.unbuffer_next_chunk()
        self.play_chunk(DAC, chunk)

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

    if minimal.args.list_devices:
        print("Available devices:")
        print(sd.query_devices())
        quit()

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
