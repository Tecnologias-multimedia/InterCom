# Don't send empty bitplanes.
#
# The sender adds to the number of received bitplanes the number of
# skipped (zero) bitplanes of the chunk sent.

# The receiver computes the first received
# bitplane (apart from the bitplane with the signs) and report a
# number of bitplanes received equal to the real number of received
# bitplanes plus the number of skipped bitplanes.

import struct
import numpy as np
from intercom import Intercom
from intercom_dfc import Intercom_DFC

if __debug__:
    import sys

class Intercom_empty(Intercom_DFC):

    def init(self, args):
        Intercom_DFC.init(self, args)

if __name__ == "__main__":
    intercom = Intercom_empty()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
