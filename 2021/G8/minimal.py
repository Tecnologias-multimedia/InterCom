#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

''' Real-time Audio Intercommunicator (minimal version). '''

import argparse
import sounddevice as sd
import numpy as np
import socket
import time
import psutil
try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    print("Unable to import argcomplete")

def spinning_cursor():
    ''' https://stackoverflow.com/questions/4995733/how-to-create-a-spinning-command-line-cursor
    '''
    while True:
        for cursor in '|/-\\':
            yield cursor
spinner = spinning_cursor()

def int_or_str(text):
    '''Helper function for argument parsing.
    '''
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-i", "--input-device", type=int_or_str, help="Input device ID or substring")
parser.add_argument("-o", "--output-device", type=int_or_str, help="Output device ID or substring")
parser.add_argument("-s", "--frames_per_second", type=float, default=44100, help="sampling rate in frames/second")
parser.add_argument("-c", "--frames_per_chunk", type=int, default=1024, help="Number of frames in a chunk")
parser.add_argument("-l", "--listening_port", type=int, default=4444, help="My listening port")
parser.add_argument("-a", "--destination_address", type=int_or_str, default="localhost", help="Destination (interlocutor's listening-) address")
parser.add_argument("-p", "--destination_port", type=int, default=4444, help="Destination (interlocutor's listing-) port")

class Minimal:
    """
    Definition a minimal InterCom (no compression, no quantization, ... only provides a bidirectional (full-duplex) transmission of raw (playable) chunks.

    Class attributes
    ----------------
    MAX_PAYLOAD_BYTES : int
        Maximum length of the payload of a UDP packet. Each chunk is sent in a different packet.
    SAMPLE_TYPE : type
        Data type used for representing the audio samples.
    NUMBER_OF_CHANNELS : int
        Number of audio channels used.

    Methods
    -------
    __init__()
    pack(chunk)
    send(packed_chunk)
    receive()
    unpack(packed_chunk)
    generate_zero_chunk()
    _record_io_and_play()
    _stream()
    run()
    """

    # Some default values:
    MAX_PAYLOAD_BYTES = 32768 # The maximum UDP packet's payload.
    SAMPLE_TYPE = np.int16    # The number of bits per sample.
    NUMBER_OF_CHANNELS = 2    # The number of channels.

    def __init__(self):
        ''' Constructor. Basically initializes the sockets stuff. '''
        print("InterCom (Minimal) is running")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", args.listening_port)
        self.sock.bind(self.listening_endpoint)
        self.chunk_time = args.frames_per_chunk / args.frames_per_second
        self.zero_chunk = self.generate_zero_chunk()
        if __debug__:
            print("\nInterCom parameters:\n")
            print(args)
            print("\nUsing device:\n")
            print(sd.query_devices(args.input_device))
            print()
            print("chunk_time =", self.chunk_time, "seconds")
            print("NUMBER_OF_CHANNELS =", self.NUMBER_OF_CHANNELS)

    def pack(self, chunk):
        ''' Builds a packet's payloads with a chunk.

        Parameters
        ----------
        chunk : numpy.ndarray
            A chunk of audio.

        Returns
        -------
        bytes
            A packed chunk.

        '''
        return chunk  # In minimal, this method does not perform any work.

    def unpack(self, packed_chunk):
        ''' Unpack a packed_chunk.

        Parameters
        ----------

        packed_chunk : bytes

            A chunk.

        Returns
        -------

        numpy.ndarray

            A chunk (a pointer to the socket's read-only buffer).
        '''

        # We need to reshape a numpy array.
        chunk = np.frombuffer(packed_chunk, self.SAMPLE_TYPE)
        chunk = chunk.reshape(args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        return chunk
    
    def send(self, packed_chunk):
        ''' Sends an UDP packet.

        Parameters
        ----------

        packed_chunk : bytes

            A packet structure with the sequence of bytes to send.

        '''
        self.sock.sendto(packed_chunk, (args.destination_address, args.destination_port))
        

    def receive(self):
        ''' Receives an UDP packet without blocking.

        Returns
        -------

        bytes

           A packed chunk.
        '''
        try:
            packed_chunk, sender = self.sock.recvfrom(self.MAX_PAYLOAD_BYTES)
            return packed_chunk
        except socket.timeout:
            raise

    def generate_zero_chunk(self):
        '''Generates a chunk with zeros that will be used when an inbound
        chunk is not available.'''
        return np.zeros((args.frames_per_chunk, self.NUMBER_OF_CHANNELS), self.SAMPLE_TYPE)

    def _record_io_and_play(self, indata, outdata, frames, time, status):
        '''Interruption handler that samples a chunk, builds a packet with the
        chunk, sends the packet, receives a packet, unpacks it to get
        a chunk, and plays the chunk.

        Parameters
        ----------

        indata : numpy.ndarray

            The chunk of audio with the recorded data.

        outdata : numpy.ndarray

            The chunk of audio with the data to play.

        frames : int16

            The number of frames in indata and outdata.

        time : CData

            Time-stamps of the first frame in indata, in outdata (that
            is time at which the callback function was called.

        status : CallbackFlags

            Indicates if underflow or overflow conditions happened
            during the last call to the callbak function.

        '''
        if __debug__:
            data = indata.copy()
            packed_chunk = self.pack(data)
        else:
            packed_chunk = self.pack(indata)
        self.send(packed_chunk)
        try:
            packed_chunk = self.receive()
            chunk = self.unpack(packed_chunk)
        except (socket.timeout, BlockingIOError):
            #chunk = np.zeros((args.frames_per_chunk, self.NUMBER_OF_CHANNELS), self.SAMPLE_TYPE)
            chunk = self.zero_chunk
            if __debug__:
                print("playing zero chunk")
        outdata[:] = chunk
        if __debug__:
            #if not np.array_equal(indata, outdata):
            #    print("indata[0] =", indata[0], "outdata[0] =", outdata[0])
            print(next(spinner), end='\b', flush=True)

    def stream(self, callback_function):
        '''Creates the stream.

        Returns
        -------
        sounddevice.Stream
           The object that records and plays audio represented in numpy arrays.
        '''
        return sd.Stream(device=(args.input_device, args.output_device),
                         dtype=self.SAMPLE_TYPE,
                         samplerate=args.frames_per_second,
                         blocksize=args.frames_per_chunk,
                         channels=self.NUMBER_OF_CHANNELS,
                         callback=callback_function)

    def run(self):
        '''Creates the stream, install the callback function, and waits for
        an enter-key pressing.'''
        #self.sock.settimeout(self.chunk_time)
        self.sock.settimeout(0)
        print("Press enter-key to quit")
        with self.stream(self._record_io_and_play):
            input()

parser.add_argument("--show_stats", action="store_true", help="shows bandwith, CPU and quality statistics")
parser.add_argument("--show_samples", action="store_true", help="shows samples values")

class Minimal__verbose(Minimal):
    ''' Verbose version of Minimal.

    Methods
    -------
    __init__()
    send(packed_chunk)
    receive()
    cycle_feedback()
    run()
    '''

    SECONDS_PER_CYCLE = 1
    
    def __init__(self):
        ''' Defines the stuff for providing the running information. '''
        super().__init__()

        self.sent_bytes_count = 0
        self.received_bytes_count = 0
        self.sent_messages_count = 0
        self.received_messages_count = 0
        self.sent_kbps = 0
        self.received_kbps = 0
        # All counters are reset at the end of each cycle.

        self.average_CPU_usage = 0
        self.average_global_CPU_usage = 0
        self.average_sent_kbps = 0
        self.average_received_kbps = 0
        self.frames_per_cycle = self.SECONDS_PER_CYCLE * args.frames_per_second
        self.chunks_per_cycle = self.frames_per_cycle / args.frames_per_chunk
        # All average values are per cycle.

        self.cycle = 1 # Infinite counter.
        
        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]

        if __debug__:
            print("SECONDS_PER_CYCLE =", self.SECONDS_PER_CYCLE)            
            print("chunks_per_cycle =", self.chunks_per_cycle)
            print("frames_per_cycle =", self.frames_per_cycle)

    def send(self, packed_chunk):
        ''' Computes the number of sent bytes and the number of sent packets. '''
        super().send(packed_chunk)
        #self.sent_bytes_count += len(packed_chunk)*np.dtype(self.SAMPLE_TYPE).itemsize*self.NUMBER_OF_CHANNELS
        self.sent_bytes_count += packed_chunk.nbytes
        self.sent_messages_count += 1

    def receive(self):
        ''' Computes the number of received bytes and the number of received packets. '''
        try:
            packed_chunk = super().receive()
            self.received_bytes_count += len(packed_chunk)
            self.received_messages_count += 1
            return packed_chunk
        except Exception:
            raise

    def stats_format(self):
        string = ""
        string += "{:5d}".format(self.cycle)
        string += "{:8d}".format(self.sent_messages_count)
        string += "{:8d}".format(self.received_messages_count)
        string += "{:8d}".format(self.sent_kbps)
        string += "{:8d}".format(self.received_kbps)
        string += "{:8d}".format(int(self.average_sent_kbps))
        string += "{:8d}".format(int(self.average_received_kbps))
        string += "{:5d}".format(int(self.CPU_usage))
        string += "{:5d}".format(int(self.average_CPU_usage))
        string += "{:5d}".format(int(self.global_CPU_usage))
        string += "{:5d}".format(int(self.average_global_CPU_usage))
        return string

    def print_stats(self):
        print(self.stats_format())

    def first_line_format(self):
        string = ""
        string += "{:5s}".format('') # cycle
        string += "{:8s}".format('') # sent_messages_count
        string += "{:8s}".format('') # received_messages_count
        string += "{:8s}".format('') # sent_kbps
        string += "{:8s}".format('') # received_kbps
        string += "{:>8s}".format("Avg.") # average_sent_kbps
        string += "{:>8s}".format("Avg.") # average_received_kbps
        string += "{:5s}".format('') # CPU_usage
        string += "{:5s}".format('') # average_CPU_usage
        string += "{:4s}".format('') # global_CPU_usage
        string += "{:>5s}".format("Global") # average_global_CPU_usage
        return string

    def print_first_line(self):
        print(self.first_line_format())

    def second_line_format(self):
        string = ""
        string += "{:5s}".format('') # cycle
        string += "{:>8s}".format("sent") # sent_messages_count
        string += "{:>8s}".format("recv.") # received_messages_count
        string += "{:>8s}".format("sent") # sent_kbps
        string += "{:>8s}".format("recv.") # received_kbps
        string += "{:>8s}".format("sent") # average_sent_kbps
        string += "{:>8s}".format("recv.") # average_received_kbps
        string += "{:5s}".format('') # CPU_usage
        string += "{:>5s}".format("Avg.") # average_CPU_usage
        string += "{:5s}".format('') # global_CPU_usage
        string += "{:>5s}".format("Avg.") # average_global_CPU_usage
        return string

    def print_second_line(self):
        print(self.second_line_format())

    def third_line_format(self):
        string = ""
        string += "{:5s}".format("cycle") # cycle
        string += "{:>8s}".format("mesgs.") # sent_messages_count
        string += "{:>8s}".format("mesgs.") # received_messages_count
        string += "{:>8s}".format("kbps") # sent_kbps
        string += "{:>8s}".format("kbps") # received_kbps
        string += "{:>8s}".format("kbps") # average_sent_kbps
        string += "{:>8s}".format("kbps") # average_received_kbps
        string += "{:>5s}".format("%CPU") # CPU_usage
        string += "{:>5s}".format("%CPU") # average_CPU_usage
        string += "{:>5s}".format("%CPU") # global_CPU_usage
        string += "{:>5s}".format("%CPU") # average_global_CPU_usage
        return string

    def print_third_line(self):
        print(self.third_line_format())

    def print_fourth_line(self):
        print(f"{'='*73}")

    def print_header(self):
        self.print_first_line()
        self.print_second_line()
        self.print_third_line();
        self.print_fourth_line()

    def print_trailer(self):
        self.print_fourth_line()
        self.print_third_line()
        self.print_second_line()
        self.print_first_line()
        
    def cycle_feedback(self):
        ''' Computes and shows the statistics. '''

        # https://en.wikipedia.org/wiki/Moving_average
        def moving_average(average, new_sample, number_of_samples):
            return average + (new_sample - average) / number_of_samples

        elapsed_time = time.time() - self.old_time
        elapsed_CPU_time = psutil.Process().cpu_times()[0] - self.old_CPU_time
        self.CPU_usage = 100 * elapsed_CPU_time / elapsed_time
        self.global_CPU_usage = psutil.cpu_percent()
        self.average_CPU_usage = moving_average(self.average_CPU_usage, self.CPU_usage, self.cycle)
        self.average_global_CPU_usage = moving_average(self.average_global_CPU_usage, self.global_CPU_usage, self.cycle)
        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]

        self.sent_kbps = int(self.sent_bytes_count * 8 / 1000 / elapsed_time)
        self.received_kbps = int(self.received_bytes_count * 8 / 1000 / elapsed_time)
        self.average_sent_kbps = moving_average(self.average_sent_kbps, self.sent_kbps, self.cycle)
        self.average_received_kbps = moving_average(self.average_received_kbps, self.received_kbps, self.cycle)

        self.print_stats()
        self.print_trailer()
        print("\033[5A")
        
        self.sent_bytes_count = 0
        self.received_bytes_count = 0
        self.sent_messages_count = 0
        self.received_messages_count = 0

        self.cycle += 1

    def print_final_averages(self):
        print('\n'*4)
        print(f"CPU usage average = {self.average_CPU_usage} %")
        print(f"Payload sent average = {self.average_sent_kbps} kilo bits per second")
        print(f"Payload received average = {self.average_received_kbps} kilo bits per second")

    def run(self):
        ''' Runs the verbose InterCom. '''
        self.sock.settimeout(0)
        print("Use CTRL+C to quit")
        self.print_header()
        try:
            with self.stream(self._record_io_and_play):
                while True:
                    time.sleep(self.SECONDS_PER_CYCLE)
                    self.cycle_feedback()
        except KeyboardInterrupt:
            self.print_final_averages()

    def show_data(self, data):
        for i in range(4):
            print(data[i], end=' ')
        print("...", end=' ')
        for i in range(args.frames_per_chunk//2 - 2, args.frames_per_chunk//2 + 2):
            print(data[i], end=' ')
        print("...", end=' ')
        for i in range(args.frames_per_chunk-4, args.frames_per_chunk):
            print(data[i], end=' ')

    def show_indata(self, indata):
        print("I =", end=' ')
        self.show_data(indata)
        print()

    def show_outdata(self, outdata):
        print("\033[7mO =", end=' ')
        self.show_data(outdata)
        print("\033[m")

    def _record_io_and_play(self, indata, outdata, frames, time, status):
        # Notice that in each call to this method, a (different) chunk is processed.

        if args.show_samples:
            self.show_indata(indata)

        super()._record_io_and_play(indata, outdata, frames, time, status)

        if args.show_samples:
            self.show_outdata(outdata)

if __name__ == "__main__":
    parser.description = __doc__
    try:
        argcomplete.autocomplete(parser)
    except Exception:
        print("argcomplete not working :-/")
    args = parser.parse_known_args()[0]
    if args.show_stats or args.show_samples:
        intercom = Minimal__verbose()
    else:
        intercom = Minimal()
    try:
        intercom.run()
    except KeyboardInterrupt:
        parser.exit("\nInterrupted by user")
