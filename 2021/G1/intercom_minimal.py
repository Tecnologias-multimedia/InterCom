#from stats import  print_final_averages
from args import get_args, show_args
from queue import PriorityQueue
from udp_receive import UdpReceiver
from udp_send import UdpSender
import heapq 
import numpy as np
assert np
import psutil
import sounddevice as sd
import struct
import threading
import time
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
        # quantization step used for compressing
        self.quantization_step = 50

        self.buffer = PriorityQueue(maxsize=self.n * 2)
        # mutex for waiting until the buffer has a large enough number
        # of chunks before playing the sound
        self.lock = threading.Lock()
        self.stats_lock = threading.Lock()
        # immediately lock the mutex
        self.lock.acquire()
        self.last_played = -1

        self.last_client_time = -1
        self.last_server_time = -1
        self.last_stats_time = -1
        self.client_cpu_time = 0
        self.server_cpu_time = 0
        self.compression_pct = 0
        self.compression_count = 0
        self.chunks_received = 0
        self.bytes_received = 0

        self.total_elapsed = 0
        self.total_elapsed_client = 0
        self.total_client_pct = 0
        self.total_elapsed_server = 0
        self.total_server_pct = 0
        self.total_throughput = 0
        self.total_chunks_received = 0
        self.total_avg_compression = 0
        self.total_times = 0

        show_args(args)

    
    def record(self, chunk_size, stream):
        """Record a chunk from the ```stream``` into a buffer.
            """
        chunk, _ = stream.read(chunk_size)
        return chunk
            
    def quantize(self, chunk):
        """Chunk quantification
            """
        return (chunk/self.quantization_step).astype(np.uint16)

    def pack(self, seq, chunk):
        """Compress and pack the ```chunk``` before sending
            """
        # recorre los canales (normalmente 2 canales), podemos hacer esto porque transponemos la matriz
        compressed_channels = [zlib.compress(self.quantize(np.ascontiguousarray(channel))) for channel in chunk.transpose()]
        size = sum(len(channel) for channel in compressed_channels)
        pack_format = f"HHB{len(compressed_channels[0])}s{len(compressed_channels[1])}s"
        packed_chunk =  struct.pack(
            pack_format,
            seq % (1 << 16),
            len(compressed_channels[0]), # tamaño del primer canal comprimido
            self.quantization_step,
            *compressed_channels, # * es para compressed_channel[0], [1], ... (expande el array)
        )
        self.stats_lock.acquire()
        self.compression_pct += 100*(1-size/4096)
        self.compression_count += 1
        self.stats_lock.release()
        return packed_chunk

    def dequantize(self, chunk, dequantization_step):
        """Chunk dequantization
            """
        return chunk*dequantization_step

    def unpack(self, packed_chunk):
        """Unpack, rebuild and decompress ```chunk``` after reception
            """
        self.chunks_received += 1
        self.bytes_received = len(packed_chunk)
        first_channel_size, = struct.unpack("H", packed_chunk[SEQ_NO_SIZE:2*SEQ_NO_SIZE])
        second_channel_size = len(packed_chunk) - first_channel_size - 2*SEQ_NO_SIZE - 1
        seq, _, dequantization_step, first_channel_bytes, second_channel_bytes = struct.unpack(
            f"HHB{first_channel_size}s{second_channel_size}s",
            packed_chunk,
        )
        first_channel = np.frombuffer(
            zlib.decompress(first_channel_bytes), 
            dtype='int16',
        )
        second_channel = np.frombuffer(
            zlib.decompress(second_channel_bytes),
            dtype='int16'
        )
        return seq, self.dequantize(np.ascontiguousarray(np.concatenate((first_channel, second_channel)).reshape(2,-1).transpose()), dequantization_step)

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
                    self.stats_lock.acquire()
                    self.last_client_time = time.perf_counter()
                    self.stats_lock.release()
                    packed_chunk = self.pack(seq, chunk)
                    self.stats_lock.acquire()
                    self.client_cpu_time += time.perf_counter() - self.last_client_time
                    self.stats_lock.release()
                    sender.send(packed_chunk, self.out_port, self.address)
                    seq += 1

    def server(self):
        """ Record a chunk with size ```frames_per_chunk``` and sends it through ```address``` and ```out_port```
            """
        with UdpReceiver(self.in_port) as receiver:
            while True:
                packed_chunk = receiver.receive(self.payload_size)
                
                self.stats_lock.acquire()
                self.last_server_time = time.perf_counter()
                self.stats_lock.release()

                chunk = self.unpack(packed_chunk)
                # ignore old chunks
                if self.should_skip_chunk(chunk[0]):
                    self.stats_lock.acquire()
                    self.server_cpu_time += time.perf_counter() - self.last_server_time
                    self.stats_lock.release()
                    continue
                
                # Store chunks in the buffer
                self.buffer.put(chunk)

                if self.buffer.qsize() >= self.n and self.lock.locked():
                    self.lock.release()

                self.stats_lock.acquire()
                self.server_cpu_time += time.perf_counter() - self.last_server_time
                self.stats_lock.release()

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

    def stats(self):
        """ Displays the program statistics by console, here is chosen the quantification step as well
            """
        threading.Timer(1, self.stats).start()
        now = time.perf_counter()
        if self.last_stats_time == -1:
            self.last_stats_time = now
            return
        elapsed = now - self.last_stats_time
        self.last_stats_time = now
        self.stats_lock.acquire()
        elapsed_server = self.server_cpu_time
        self.server_cpu_time = 0
        elapsed_client = self.client_cpu_time
        self.client_cpu_time = 0
        avg_compression = self.compression_pct / self.compression_count
        chunks_received = self.chunks_received
        bytes_received = self.bytes_received
        self.bytes_received = self.chunks_received = self.compression_pct = self.compression_count = 0
        
        self.stats_lock.release()
        client_pct = 100 * elapsed_client / elapsed
        server_pct = 100 * elapsed_server / elapsed
        throughput = bytes_received*8/elapsed/1024
        
        self.verbose(elapsed, elapsed_client, client_pct, elapsed_server, server_pct, throughput, chunks_received, avg_compression)
        
        self.total_times += 1
        self.total_elapsed += elapsed
        self.total_elapsed_client += elapsed_client
        self.total_client_pct += client_pct
        self.total_elapsed_server += elapsed_server
        self.total_server_pct += server_pct
        self.total_throughput += throughput
        self.total_chunks_received += chunks_received
        self.total_avg_compression += avg_compression

        chunks_per_second = chunks_received / elapsed
        if chunks_per_second <= 37:
            self.quantization_step = min(250, 1 + int(self.quantization_step * 1.2))
        elif chunks_per_second >= 43:
            self.quantization_step = max(1, int(self.quantization_step * 0.8))

    def final_averages(self):
        avg_elapsed = self.total_elapsed / self.total_times
        avg_elapsed_client = self.total_elapsed_client / self.total_times
        avg_client_pct = self.total_client_pct / self.total_times
        avg_elapsed_server = self.total_elapsed_server / self.total_times
        avg_server_pct = self.total_server_pct / self.total_times
        avg_throughput = self.total_throughput / self.total_times
        avg_chunks_received = self.total_chunks_received / self.total_times
        avg_avg_compression = self.total_avg_compression / self.total_times

        print(f"------- AVERAGE STATS -------")
        self.verbose(avg_elapsed, avg_elapsed_client, avg_client_pct, avg_elapsed_server, avg_server_pct, avg_throughput, avg_chunks_received, avg_avg_compression)
    
    def verbose(self, elapsed, elapsed_client, client_pct, elapsed_server, server_pct, throughput, chunks_received, avg_compression):
        print(f"stats from the last {elapsed:.3f} seconds:")
        print(f"\t> client CPU usage: {elapsed_client:.3f} seconds, {client_pct:.2f}%")
        print(f"\t> server CPU usage: {elapsed_server:.3f} seconds, {server_pct:.2f}%")
        print(f"\t> total CPU usage: {elapsed_client + elapsed_server:.3f} seconds, {server_pct + client_pct:.2f}%")
        print(f"\t> system CPU usage: {psutil.cpu_percent():.2f}%")
        print(f"\t> {chunks_received} messages received, {throughput:.1f} Kbps")
        print(f"\t> average compression: {avg_compression:.1f}%")
        print(f"\t> quantization step: {self.quantization_step}")

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
        intercom.stats()
    except KeyboardInterrupt:
        intercom.final_averages()