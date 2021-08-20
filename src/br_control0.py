#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''To control the quantization step, the number of lost chunks is added to it. Otherwise, the quantization step is decremented by 1 each second.'''

import time
import minimal
import br_control
import logging

class BR_Control0(br_control.BR_Control):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def data_flow_control(self):
        while True:
            self.number_of_lost_packets = self.number_of_sent_chunks - self.number_of_received_chunks
            self.quantization_step += self.number_of_lost_packets
            if self.quantization_step < minimal.args.minimal_quantization_step:
                self.quantization_step = minimal.args.minimal_quantization_step
            self.number_of_lost_packets = self.number_of_sent_chunks - self.number_of_received_chunks - 1
            self.number_of_sent_chunks = 0
            self.number_of_received_chunks = 0
            time.sleep(1)

class BR_Control0__verbose(BR_Control0, br_control.BR_Control__verbose):
    
    def __init__(self):
        if __debug__:
            print("Running BR_Control0__verbose.__init__")
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
        if __debug__:
            print("argcomplete not working :-/")
        else:
            pass
    minimal.args = minimal.parser.parse_args()
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = BR_Control0__verbose()
    else:
        intercom = BR_Control0()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
