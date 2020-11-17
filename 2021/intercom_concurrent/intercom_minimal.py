import sounddevice as sd
import threading
from udp_send import UdpSender
from udp_receive import UdpReceiver
from args import get_args, show_args
import struct
import heapq 
from queue import PriorityQueue
import numpy
assert numpy

# Size of the sequence number in bytes
SEQ_NO_SIZE = 8

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
        self.n            = args.buffer_size

        self.buffer = PriorityQueue(maxsize=self.n * 2)
        # mutex for waiting until the buffer has a large enough number
        # of chunks before playing the sound
        self.lock = threading.Lock()
        # immediately lock the mutex
        self.lock.acquire()
        self.last_played = -1

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
            
    def pack(self, seq, chunk):
        """TODO
            """
        chunk_bytes = bytes(chunk)
        return struct.pack(f"Q {len(chunk_bytes)}s", seq, chunk_bytes)

    def unpack(self, packed_chunk):
        """TODO
            """
        return struct.unpack(f"Q {len(packed_chunk) - SEQ_NO_SIZE}s", packed_chunk)

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

        seq = 0
        with UdpSender() as sender:
            while True:
                chunk = self.record(self.frames_per_chunk, stream)
                if not chunk: 
                    continue
                packed_chunk = self.pack(seq, chunk)
                sender.send(packed_chunk, self.out_port, self.address)
                seq += 1

    def server(self):
        """ Record a chunk with size ```frames_per_chunk``` and sends it through ```address``` and ```out_port```
            """
        with UdpReceiver(self.in_port) as receiver:
            while True:
                packed_chunk = receiver.receive(self.payload_size)
                chunk = self.unpack(packed_chunk)
                # ignore old chunks
                if self.should_skip_chunk(chunk[0]):
                    continue
                
                # Store chunks in the buffer
                self.buffer.put(chunk)

                if self.buffer.qsize() >= self.n and self.lock.locked():
                    self.lock.release()

    def playback(self):
        """ Manage and play chunks in the buffer
            """
        stream = sd.RawOutputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16')
        stream.start()
        while True:
            # Wait until half of the buffer is full 
            if self.buffer.qsize() <= self.n:
                self.lock.acquire()
            seq, chunk = self.buffer.get()
            # ignore old chunks
            if self.should_skip_chunk(seq):
                continue
            self.last_played = seq
            self.play(chunk, stream)

    def should_skip_chunk(self, seq):
        """ Avoid inserting old chunks in the buffer according to their ```sequence``` number
            """
        #Check if the input chunk sequence differs from the current execution sequence 
        if seq < self.last_played:
            dif = self.last_played - seq
            # If the "id" of the chunk is too old, restart the execution sequence
            if dif > self.n * 2:
                print(f"received very old chunk ({dif} packets old), updating seq no")
                self.last_played = seq - 1
                return False
            # If the difference with the execution sequence is small, those packages are dropped
            else:
                print(f"dropped old chunk ({dif} packets old)")
                return True
        else:
            return False


if __name__ == "__main__":
    # Get args
    parser = get_args()
    args = parser.parse_args()
    # Start the program
    intercom = InterCom(args)
    # Threads
    clientT = threading.Thread(target=intercom.client)
    serverT = threading.Thread(target=intercom.server)
    playbackT = threading.Thread(target=intercom.playback)
    clientT.start()
    serverT.start()
    playbackT.start()