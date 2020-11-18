import sounddevice as sd
import threading
from udp_send import UdpSender
from udp_receive import UdpReceiver
from args import get_args, show_args
#import numpy # Por ahora no usaremos numpy porque no le sacaremos provecho
#assert numpy

class InterCom():
    def __init__(self, args):
        # audio args
        self.number_of_channels = args.number_of_channels
        self.frames_per_second  = args.frames_per_second
        self.frames_per_chunk   = args.frames_per_chunk
    
        # network args
        self.payload_size = args.payload_size
        self.in_port      = args.in_port
        self.out_port     = args.out_port
        self.address      = args.address

        show_args(args)

    
    def record(self, chunk_size, stream):
        """Record a chunk from the ```stream``` into a buffer.

            Parameters
            ----------
            chunk_size : int
                The number of frames to be read.

            stream : buffer
                Raw stream for playback and recording.

            Returns
            -------
            chunk : sd.RawStream
                A buffer of interleaved samples. The buffer contains
                samples in the format specified by the *dtype* parameter
                used to open the stream, and the number of channels
                specified by *channels*.
            """

        chunk, _ = stream.read(chunk_size)
        return chunk
            
    def pack(self, chunk):
        """TODO
            """
        return chunk

    def unpack(self, packed_chunk):
        """TODO
            """
        return packed_chunk

    def play(self, chunk, stream):
        """Write samples to the stream.

            Parameters
            ----------
            chunk : buffer
                A buffer of interleaved samples. The buffer contains
                samples in the format specified by the *dtype* parameter
                used to open the stream, and the number of channels
                specified by *channels*.

            stream : sd.RawStream
                Raw stream for playback and recording.
            """
        stream.write(chunk)

    def client(self):
        """ Receive a chunk from ```in_port``` and plays it.
            """
        stream = sd.RawInputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16')
        stream.start()
        with UdpSender() as sender:
            while True:
                chunk = self.record(self.frames_per_chunk, stream)
                packed_chunk = self.pack(chunk)
                sender.send(packed_chunk, self.out_port, self.address)

    def server(self):
        """ Record a chunk with size ```frames_per_chunk``` and sends it through ```address``` and ```out_port```
            """
        stream = sd.RawOutputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16')
        stream.start()
        with UdpReceiver(self.in_port) as receiver:
            while True:
                packed_chunk = receiver.receive(self.payload_size)
                chunk = self.unpack(packed_chunk)
                self.play(chunk, stream)

if __name__ == "__main__":
    # Get args
    parser = get_args()
    args = parser.parse_args()
    # Start the program
    intercom = InterCom(args)
    # Threads
    clientT = threading.Thread(target=intercom.client)
    serverT = threading.Thread(target=intercom.server)
    clientT.start()
    serverT.start()