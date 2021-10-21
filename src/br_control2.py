#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''The quantization step is multipled by 2 each time 2 lost chunks has been detected. Otherwise, the quantization step is divided by 1.1.'''

import time
import minimal
import br_control
import logging

class BR_Control2(br_control.BR_Control):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def data_flow_control(self):
        while True:
            self.number_of_lost_packets = self.number_of_sent_chunks - self.number_of_received_chunks
            if self.number_of_lost_packets > 2:
                self.quantization_step *= 2
            self.quantization_step = int(self.quantization_step / 1.1)
            if self.quantization_step < minimal.args.minimal_quantization_step:
                self.quantization_step = minimal.args.minimal_quantization_step
            self.number_of_sent_chunks = 0
            self.number_of_received_chunks = 0
            time.sleep(1)

class BR_Control2__verbose(BR_Control2, br_control.BR_Control__verbose):
    
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
    minimal.args = minimal.parser.parse_args()
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = BR_Control2__verbose()
    else:
        intercom = BR_Control2()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
