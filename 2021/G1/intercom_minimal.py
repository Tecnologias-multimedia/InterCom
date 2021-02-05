#from stats import  print_final_averages
from args import get_args, show_args
from queue import PriorityQueue
from udp_receive import UdpReceiver
from udp_send import UdpSender
from temporal_decorrelate import Temporal_decorrelation as temp_dec
import heapq 
import numpy as np
assert np
import os
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

        os.environ['SDL_AUDIODRIVER'] = 'dsp'
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
        self.wavelet      = args.wavelet_name
        self.level        = args.levels

        # using temporal decorrelate and stereo decorrelate
        self.temp_dec = temp_dec(self.wavelet, self.level)
        
        # quantization step used for compressing
        self.quantization_step = 1

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

    def pack(self, seq, chunk):
        """Compress and pack the ```chunk``` before sending
            """
        # recorre los canales (normalmente 2 canales), podemos hacer esto porque transponemos la matriz
        #print("Antes de decorrelacion -> ", chunk)
        coefs = self.temp_dec.MST_analyze(chunk)
        coefs = self.temp_dec.DWT_analyze(coefs)
        k = self.temp_dec.quantize(coefs, self.quantization_step)
        #print("Despues de decorrelación -> ", chunk)

        compressed_chunk = zlib.compress(k) # reshape(-1) deja en una línea el array
        size_chunk = len(compressed_chunk)
        pack_format = f"HH{size_chunk}s"
        packed_chunk =  struct.pack(
            pack_format,
            seq % (1 << 16),
            self.quantization_step,
            compressed_chunk, 
        )
        self.stats_lock.acquire()
        self.compression_pct += 100*(1-size_chunk/4096)
        self.compression_count += 1
        self.stats_lock.release()
        return packed_chunk

    def unpack(self, packed_chunk):
        """Unpack, rebuild and decompress ```chunk``` after reception
            """
        self.chunks_received += 1
        self.bytes_received = len(packed_chunk)

        seq, dequantization_step, compressed_chunk_bytes = struct.unpack(f"HH{len(packed_chunk) - 2*SEQ_NO_SIZE}s", packed_chunk)        

        k = np.frombuffer(
            zlib.decompress(compressed_chunk_bytes), 
            dtype='int32',
        )
        dequantized_chunk = self.temp_dec.dequantize(k, dequantization_step)
        synthesized_chunk = self.temp_dec.DWT_synthesize(dequantized_chunk)
        synthesized_chunk = self.temp_dec.MST_synthesize(synthesized_chunk)
        return seq, synthesized_chunk

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
        avg_compression = 0
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

        # 1000 max con qs=1
        # 100 minb con qs=250
        chunks_per_second = chunks_received / elapsed
        if chunks_per_second <= 39:
            self.quantization_step = min(250, int(self.quantization_step * 1.2))
        elif chunks_per_second >= 43:
            self.quantization_step = max(1, int(self.quantization_step * 0.8))

    def final_averages(self):
        threading.Timer(5, self.final_averages).start()
        
        avg_elapsed = self.total_elapsed / self.total_times
        avg_elapsed_client = self.total_elapsed_client / self.total_times
        avg_client_pct = self.total_client_pct / self.total_times
        avg_elapsed_server = self.total_elapsed_server / self.total_times
        avg_server_pct = self.total_server_pct / self.total_times
        avg_throughput = self.total_throughput / self.total_times
        avg_chunks_received = self.total_chunks_received / self.total_times
        avg_avg_compression = self.total_avg_compression / self.total_times

        print(f"\n------- AVERAGE STATS OF {self.total_times} -------\n")
        self.verbose(avg_elapsed, avg_elapsed_client, avg_client_pct, avg_elapsed_server, avg_server_pct, avg_throughput, avg_chunks_received, avg_avg_compression)
        print(f"\n------- END AVERAGE STATS -----\n")
    
    def verbose(self, elapsed, elapsed_client, client_pct, elapsed_server, server_pct, throughput, chunks_received, avg_compression):
        print(f"stats from the last {elapsed:.3f} seconds:")
        print(f"\t> client CPU usage: {elapsed_client:.3f} seconds, {client_pct:.2f}%")
        print(f"\t> server CPU usage: {elapsed_server:.3f} seconds, {server_pct:.2f}%")
        print(f"\t> total CPU usage: {elapsed_client + elapsed_server:.3f} seconds, {server_pct + client_pct:.2f}%")
        print(f"\t> system CPU usage: {psutil.cpu_percent():.2f}%")
        print(f"\t> {int(chunks_received)} messages received, {throughput:.2f} Kbps")
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
        time.sleep(2)
        intercom.stats()
        time.sleep(5)
        intercom.final_averages()
    except KeyboardInterrupt:
        pass