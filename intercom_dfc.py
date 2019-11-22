# Implementing a Data-Flow Control algorithm.

from intercom_bitplanes import Intercom_bitplanes
from intercom_binaural import Intercom_binaural

class Intercom_dfc(Intercom_binaural):

    def init(self, args):
        Intercom_binaural.init(self, args)
        self.received_bitplanes_per_chunk = [0]*self.cells_in_buffer

    def receive_and_buffer(self):
        received_chunk_number = Intercom_binaural.receive_and_buffer(self)
        self.received_bitplanes_per_chunk[received_chunk_number % self.cells_in_buffer] += 1
        print(self.received_bitplanes_per_chunk)
        return received_chunk_number

    def record_and_send(self, indata):
        #self.number_of_bitplanes_to_send = self.received_bitplanes_per_chunk[self.played_chunk_number % self.cells_in_buffer]
        self.number_of_bitplanes_to_send = 10*2
        Intercom_binaural.record_and_send(self, indata)
#    def record_send_and_play_stereo(self, indata, outdata, frames, time, status):
#        Intercom_binaural.record_send_and_play(self, indata, outdata, frames, time, status)
#        self.received_bitplanes_per_chunk [self.played_chunk_number % self.cells_in_buffer] = 0
        
if __name__ == "__main__":
    intercom = Intercom_dfc()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
