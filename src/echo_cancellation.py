#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Simple echo cancellation.'''

import numpy as np
import struct
import math
import logging

import pygame

import minimal
import buffer

class Echo_Cancellation(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        self.delay = 500 # In frames
        self.attenuation = 0.2

class Echo_Cancellation__verbose(Echo_Cancellation, buffer.Buffering__verbose):
    def __init__(self):
        super().__init__()
        self.window_heigh = 512
        self.screen = pygame.display.set_mode((minimal.args.frames_per_chunk, self.window_heigh))


    def play_chunk(self, DAC, chunk):
        self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
        chunk = chunk.reshape(minimal.args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        channel = chunk[:, 0]
        corr = np.correlate(a=channel, v=channel, mode='full')[len(channel)-1:]
        #print(len(corr))
        max_index = np.argmax(corr)
        max_val = corr[max_index]
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
                break
        self.screen.fill((0, 0, 0))
        color = (0, 128, 0)
        for i in range(len(corr)):
            #pygame.draw.line(self.screen, color, (i, self.window_heigh), (i, int(self.window_heigh - corr/100)))
            pygame.draw.line(self.screen, color, (i, self.window_heigh), (i, 10))
        #pygame.display.flip()
        pygame.display.update()
        DAC[:] = chunk #- np.roll(chunk, 0)

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
