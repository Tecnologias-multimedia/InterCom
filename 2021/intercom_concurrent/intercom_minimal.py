import sounddevice as sd
import threading
from udp_send import UdpSender
from udp_receive import UdpReceiver
from args import get_args, show_args
#from stats import  print_final_averages
import struct
import heapq 
from queue import PriorityQueue
import numpy as np
assert np
import zlib

# Size of the sequence number in bytes
SEQ_NO_SIZE = 2

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
            """
        chunk, _ = stream.read(chunk_size)
        return chunk
            
    def pack(self, seq, chunk):
        """TODO
            """
        compressed_chunk = zlib.compress(chunk.transpose().reshape(-1)) # reshape(-1) deja en una línea el array
        size = len(compressed_chunk)
        print("size", size, "bytes, compression rate", "{:.2f}%".format(100*(1-size/4096)))


        pack_format = f"H{len(compressed_chunk)}s"
        return struct.pack(
            pack_format, 
            seq, 
            compressed_chunk,
        )

    def unpack(self, packed_chunk):
        """TODO
            """
        seq, compressed_chunk_bytes = struct.unpack(f"H {len(packed_chunk) - SEQ_NO_SIZE}s", packed_chunk)
          
        chunk = np.frombuffer(
            zlib.decompress(compressed_chunk_bytes), 
            dtype='int16',
        )

        return seq, np.ascontiguousarray(chunk.reshape(2,-1).transpose())

    def play(self, chunk, stream):
        """Write samples to the stream.
            """
        stream.write(chunk)

    def client(self):
        """ Receive a chunk from ```in_port``` and plays it.
            """
        with sd.InputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16') as stream:
            seq = 0
            with UdpSender() as sender:
                while True:
                    chunk = self.record(self.frames_per_chunk, stream)
                    if chunk.size == 0: 
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
        with sd.OutputStream(samplerate=self.frames_per_second, channels=self.number_of_channels, dtype='int16') as stream:
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
    try:
        clientT.start()
        serverT.start()
        playbackT.start()
    except KeyboardInterrupt:
        pass
        #print_final_averages()