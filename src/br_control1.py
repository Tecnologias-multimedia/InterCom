#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (br_control1.py). '''

import time
import minimal
import br_control

class BR_Control1(br_control.BR_Control):
    '''The quantization step is the number of lost packed minus 1.

    '''

    def __init__(self):
        if __debug__:
            print("Running BR_Control1.__init__")
        super().__init__()

    def data_flow_control(self):
        while True:
            self.number_of_lost_packets = self.number_of_sent_chunks - self.number_of_received_chunks - 1
            self.quantization_step += self.number_of_lost_packets
            if self.quantization_step < minimal.args.minimal_quantization_step:
                self.quantization_step = minimal.args.minimal_quantization_step
            self.number_of_sent_chunks = 0
            self.number_of_received_chunks = 0
            time.sleep(1)

class BR_Control1__verbose(BR_Control1, br_control.BR_Control__verbose):
    
    def __init__(self):
        if __debug__:
            print("Running BR_Control1__verbose.__init__")
        super().__init__()

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

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
        intercom = BR_Control1__verbose()
    else:
        intercom = BR_Control1()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
