#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

# Probar a comprimir (logaritmicamente) la salida por los altavoces con una ganancia proporcional al parecido entre lo que sale por los altavoces (lo que llega a través de la red) y lo que captura el micrófono.


'''Feedback supression (template).'''

import logging

import minimal
import buffer
        
class Feedback_Supression(buffer.Buffering):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)
        
class Feedback_Supression__verbose(Feedback_Supression, buffer.Buffering__verbose):
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
        intercom = Feedback_Supression__verbose()
    else:
        intercom = Feedback_Supression()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")
    finally:
       intercom.print_final_averages()
