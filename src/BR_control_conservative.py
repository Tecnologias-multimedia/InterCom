#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Bit-rate control using quantization. Both channels are quantized
using the same constant step. The quantization step is multipled by 2
each time 2 lost chunks has been detected. Otherwise, the quantization
step size is divided by 1.1.'''

import time
import logging

import minimal
import BR_control_no

class BR_Control_Conservative(BR_control_no.BR_Control_No):

    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def data_flow_control(self):
        while True:
            self.number_of_lost_packets = self.number_of_sent_chunks - self.number_of_received_chunks
            if self.number_of_lost_packets > 2:
                self.quantization_step_size *= 2
            self.quantization_step_size = int(self.quantization_step_size / 1.1)
            if self.quantization_step_size < minimal.args.minimal_quantization_step_size:
                self.quantization_step_size = minimal.args.minimal_quantization_step_size
            self.number_of_sent_chunks = 0
            self.number_of_received_chunks = 0
            time.sleep(self.rate_control_period)

class BR_Control_Conservative__verbose(BR_Control_Conservative, BR_control_no.BR_Control_No__verbose):
    pass
    #def __init__(self):
    #    super().__init__()

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
        intercom = BR_Control_Conservative__verbose()
    else:
        intercom = BR_Control_Conservative()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
