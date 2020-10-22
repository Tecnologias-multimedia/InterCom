''' Real-time Audio Intercommunicator (minimal version). '''

import argparse
import logging
import sounddevice as sd
import numpy as np
import socket
import time
import threading
import psutil

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
parser.add_argument("-v", "--verbose", help="Provides running information", action="store_true")

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
    MAX_PAYLOAD_BYTES = 32768
    SAMPLE_TYPE = np.int16
    NUMBER_OF_CHANNELS = 2

    def __init__(self):
        ''' Constructor. Basically initializes the sockets stuff. '''
        self.sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", args.listening_port)
        self.receiving_socket.bind(self.listening_endpoint)
        self.receiving_socket.settimeout(0)
        self.zero_chunk = self.generate_zero_chunk()

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

    def send(self, packed_chunk):
        ''' Sends an UDP packet.

        Parameters
        ----------

        packed_chunk : bytes

            A packet structure with the sequence of bytes to send.

        '''
        self.sending_socket.sendto(packed_chunk, (args.destination_address, args.destination_port))

    def receive(self):
        ''' Receives an UDP packet without blocking.

        Returns
        -------

        bytes

           A packed chunk.
        '''
        try:
            packed_chunk, sender = self.receiving_socket.recvfrom(self.MAX_PAYLOAD_BYTES)
            return packed_chunk
        except BlockingIOError:
            raise

    def unpack(self, packed_chunk):
        ''' Unpack a packed_chunk.

        Parameters
        ----------

        packed_chunk : bytes

            A packet.

        Returns
        -------

        numpy.ndarray

            A chunk (a pointer to the socket's read-only buffer).
        '''
           
        chunk = np.frombuffer(packed_chunk, self.SAMPLE_TYPE)  # We need to reshape a numpy array
        chunk = chunk.reshape(args.frames_per_chunk, self.NUMBER_OF_CHANNELS)
        return chunk
    
    def generate_zero_chunk(self):
        '''Generates a chunk with zeros that will be used when an inbound chunk is not available. '''
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
            print("indata  =", end=' ')
            for i in range(4):
                print(indata[i], end=' ')
            print("...", end=' ')
            for i in range(args.frames_per_chunk//2 - 2, args.frames_per_chunk//2 + 2):
                print(indata[i], end=' ')
            print("...", end=' ')
            for i in range(args.frames_per_chunk-4, args.frames_per_chunk):
                print(indata[i], end=' ')
            print()
        packed_chunk = self.pack(indata)
        self.send(packed_chunk)
        try:
            packed_chunk = self.receive()
            chunk = self.unpack(packed_chunk)
        except BlockingIOError:
            #chunk = np.zeros((args.frames_per_chunk, self.NUMBER_OF_CHANNELS), self.SAMPLE_TYPE)
            chunk = self.zero_chunk
        if __debug__:
            print("\033[7moutdata =", end=' ')
            for i in range(4):
                print(chunk[i], end=' ')
            print("...", end=' ')
            for i in range(args.frames_per_chunk//2 - 2, args.frames_per_chunk//2 + 2):
                print(chunk[i], end=' ')
            print("...", end=' ')
            for i in range(args.frames_per_chunk-4, args.frames_per_chunk):
                print(chunk[i], end=' ')
            print("\033[m")
        outdata[:] = chunk
        if __debug__:
            print(next(spinner), end='\b', flush=True)

    def stream(self):
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
                         callback=self._record_io_and_play)

    def run(self):
        '''Creates the stream, install the callback function, and waits for
        an enter-key pressing.'''
        with self.stream():
            print("InterCom running ... press enter-key to quit")
            input()

class Minimal__verbose(Minimal):
    ''' Verbose version of a Minimal InterCom.'''
    
    def __init__(self):
        ''' Defines the stuff for providing the running information. '''
        print("\nInterCom parameters:\n")
        print(args)
        super().__init__()
        print("\nUsing device:\n")
        print(sd.query_devices(args.input_device))
        self.CPU_accumulated_usage = 0
        self.CPU_average_usage = 0
        self.global_CPU_accumulated_usage = 0
        self.global_CPU_average_usage = 0
        self.number_of_samples = 0
        self.sent_bytes_counter = 0
        self.received_bytes_counter = 0
        self.sent_messages_counter = 0
        self.received_messages_counter = 0

    def send(self, packed_chunk):
        ''' Computes the number of sent bytes and the number of sent packets. '''
        super().send(packed_chunk)
        #self.sent_bytes_counter += len(packed_chunk)*np.dtype(self.SAMPLE_TYPE).itemsize*self.NUMBER_OF_CHANNELS
        self.sent_bytes_counter += packed_chunk.nbytes
        self.sent_messages_counter += 1

    def receive(self):
        ''' Computes the number of received bytes and the number of received packets. '''
        try:
            packed_chunk = super().receive()
            self.received_bytes_counter += len(packed_chunk)
            self.received_messages_counter += 1
            return packed_chunk
        except BlockingIOError:
            raise

    def _print_feedback(self):
        ''' Conputes and shows the statistics. '''
        elapsed_time = time.time() - self.old_time
        elapsed_CPU_time = psutil.Process().cpu_times()[0] - self.old_CPU_time
        self.CPU_usage = 100 * elapsed_CPU_time / elapsed_time
        self.global_CPU_usage = psutil.cpu_percent()
        self.CPU_accumulated_usage += self.CPU_usage
        self.global_CPU_accumulated_usage += self.global_CPU_usage
        try:
            self.CPU_average_usage = self.CPU_accumulated_usage / self.number_of_samples
            self.global_CPU_average_usage = self.global_CPU_accumulated_usage / self.number_of_samples
        except ZeroDivisionError:
            self.CPU_average_usage = 0
            self.global_CPU_average_usage = 0
        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]
        sent = int(self.sent_bytes_counter * 8 / 1000 / elapsed_time)
        received = int(self.received_bytes_counter * 8 / 1000 / elapsed_time)
        self.sent_total += sent
        try:
            self.sent_average = self.sent_total/self.number_of_samples
        except ZeroDivisionError:
            self.sent_average = 0
        self.received_total += received
        try:
            self.received_average = self.received_total/self.number_of_samples
        except ZeroDivisionError:
            self.received_average = 0
        print(f"{self.sent_messages_counter:10d}{self.received_messages_counter:10d}{sent:10d}{received:10d}{int(self.sent_average):10d}{int(self.received_average):10d}{int(self.CPU_usage):5d}{int(self.CPU_average_usage):5d}{int(self.global_CPU_usage):5d}{int(self.global_CPU_average_usage):5d} {self.number_of_samples}")
        self.sent_bytes_counter = 0
        self.received_bytes_counter = 0
        self.sent_messages_counter = 0
        self.received_messages_counter = 0
        self.number_of_samples += 1
    
    def run(self):
        ''' Runs the verbose InterCom. '''
        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]
        self.sent_total = 0
        self.received_total = 0
        print()
        print("Use CTRL+C to quit")
        print(f"{'':>10s}{'':>10s}{'':>10s}{'':>10s}{'Avg.':>10s}{'Avg.':>10s}{'':>10s}{'Global':>10s}");
        print(f"{'sent':>10s}{'received':>10s}{'sent':>10s}{'received':>10s}{'sent':>10s}{'received':>10s}{'':>5s}{'Avg.':>5s}{'':>5s}{'Avg.':>5s}");
        print(f"{'messages':>10s}{'messages':>10s}{'kbps':>10s}{'kbps':>10s}{'kbps':>10s}{'kbps':>10s}{'%CPU':>5s}{'%CPU':>5s}{'%CPU':>5s}{'%CPU':>5s}")
        print(f"{'='*80}")
        try:
            with self.stream():
                while True:
                    self._print_feedback()
                    time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nCPU usage average = {self.CPU_average_usage} %")
            print(f"Payload sent average = {self.sent_average} kilo bits per second")
            print(f"Payload received average = {self.received_average} kilo bits per second")

if __name__ == "__main__":
    parser.description = __doc__
    args = parser.parse_args()
    if args.verbose:
        intercom = Minimal__verbose()
    else:
        intercom = Minimal()
    try:
        intercom.run()
    except KeyboardInterrupt:
        parser.exit("\nInterrupted by user")
    except Exception as e:
        parser.exit(type(e).__name__ + ": " + str(e))
