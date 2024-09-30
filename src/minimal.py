#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''A minimal InterCom (no compression, no quantization, no transform, ... only provides a bidirectional (full-duplex) transmission of raw (playable) chunks. '''

import os
import signal
import argparse
import sounddevice as sd # If "pip install sounddevice" fails, install the "libportaudio2" system package
import numpy as np
import socket
import time
import psutil
import logging
import soundfile as sf
import logging
#FORMAT = "%(module)s: %(message)s"
FORMAT = "(%(levelname)s) %(module)s: %(message)s"
#logging.basicConfig(format=FORMAT)
logging.basicConfig(format=FORMAT, level=logging.INFO)

def spinning_cursor():
    ''' https://stackoverflow.com/questions/4995733/how-to-create-a-spinning-command-line-cursor'''
    while True:
        for cursor in '|/-\\':
            yield cursor
spinner = spinning_cursor()

def int_or_str(text):
    '''Helper function for argument parsing.'''
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-i", "--input-device", type=int_or_str, help="Input device ID or substring")
parser.add_argument("-o", "--output-device", type=int_or_str, help="Output device ID or substring")
parser.add_argument("-d", "--list-devices", action="store_true", help="Print the available audio devices and quit")
parser.add_argument("-s", "--frames_per_second", type=float, default=44100, help="sampling rate in frames/second")
parser.add_argument("-c", "--frames_per_chunk", type=int, default=1024, help="Number of frames in a chunk")
parser.add_argument("-l", "--listening_port", type=int, default=4444, help="My listening port")
parser.add_argument("-a", "--destination_address", type=int_or_str, default="localhost", help="Destination (interlocutor's listening) address")
parser.add_argument("-p", "--destination_port", type=int, default=4444, help="Destination (interlocutor's listing-) port")
parser.add_argument("-f", "--filename", type=str, help="Use a wav/oga/... file instead of the mic data")
parser.add_argument("-t", "--reading_time", type=int, help="Time reading data (mic or file) (only with effect if --show_stats or --show_data is used)")
parser.add_argument("-n", "--number_of_channels", type=int, default=2, help="Number of channels") # Notice that, currently, in OSX systems, the number of channels must be 1.

class Minimal:
    # Some default values:
    MAX_PAYLOAD_BYTES = 32768 # The maximum UDP packet's payload.
    #SAMPLE_TYPE = np.int16    # The number of bits per sample.

    def __init__(self):
        ''' Constructor. Basically initializes the sockets stuff. '''
        logging.info(__doc__)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", args.listening_port)
        self.sock.bind(self.listening_endpoint)
        self.chunk_time = args.frames_per_chunk / args.frames_per_second
        logging.info(f"chunk_time = {self.chunk_time} seconds")
        self.zero_chunk = self.generate_zero_chunk()

        if args.filename:
            logging.info(f"Using \"{args.filename}\" as input")
            self.wavfile = sf.SoundFile(args.filename, 'r')
            self._handler = self._read_IO_and_play
            self.stream = self.file_stream
        else:
            self._handler = self._record_IO_and_play
            self.stream = self.mic_stream

        #self.input_exhausted = False

    def pack(self, chunk):
        '''Builds a packet's payloads with a chunk.'''
        return chunk  # In minimal, this method does not perform any work.

    def unpack(self, packed_chunk):
        '''Unpack a packed_chunk.'''

        # We need to reshape packed_chunk, that comes as sequence of
        # bytes, as a NumPy array.
        chunk = np.frombuffer(packed_chunk, np.int16)
        chunk = chunk.reshape(args.frames_per_chunk, args.number_of_channels)
        return chunk

    def send(self, packed_chunk):
        '''Sends an UDP packet.'''
        try:
            self.sock.sendto(packed_chunk, (args.destination_address, args.destination_port))
        except BlockingIOError:
            pass

    def receive(self):
        '''Receives an UDP packet without blocking.'''
        try:
            packed_chunk, sender = self.sock.recvfrom(self.MAX_PAYLOAD_BYTES)
            return packed_chunk
        except socket.timeout:
            raise

    def generate_zero_chunk(self):
        '''Generates a chunk with zeros that will be used when an inbound
        chunk is not available.

        '''
        return np.zeros((args.frames_per_chunk, args.number_of_channels), np.int16)

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        '''Interruption handler that samples a chunk, builds a packet with the
        chunk, sends the packet, receives a packet, unpacks it to get
        a chunk, and plays the chunk.

        Parameters
        ----------

        ADC : numpy.ndarray

            Holds the last recorded chunk.

        DAC : numpy.ndarray

            Accepts a chunk to play.

        frames : int16

            The number of frames in a chunk handled by ADC and DAC.

        time : CData

            Time-stamps of the first frame in chunk returned by the
            ADC, and accepted by the DAC (that is time at which the
            callback function was called).

        status : CallbackFlags

            Indicates if underflow or overflow (underrrun) conditions happened
            during the last call to the callbak function.

        '''
        # (1) record() implicit
        # (2) pack()
        if __debug__:
            data = ADC.copy()
            packed_chunk = self.pack(data)
        else:
            packed_chunk = self.pack(ADC)
        # (3) send()
        self.send(packed_chunk)
        # (4) receive() and (5) unpack()
        try:
            packed_chunk = self.receive()
            chunk = self.unpack(packed_chunk)
        except (socket.timeout, BlockingIOError):
            #chunk = np.zeros((args.frames_per_chunk, args.number_of_channels), self.SAMPLE_TYPE)
            chunk = self.zero_chunk
            logging.debug("playing zero chunk")
        # (6) play()
        DAC[:] = chunk
        if __debug__:
            #if not np.array_equal(ADC, DAC):
            #    print("ADC[0] =", ADC[0], "DAC[0] =", DAC[0])
            print(next(spinner), end='\b', flush=True)

    def read_chunk_from_file(self):
        chunk = self.wavfile.buffer_read(args.frames_per_chunk, dtype='int16')
        #print(len(chunk), args.frames_per_chunk)
        if len(chunk) < args.frames_per_chunk*4:
            logging.warning("Input exhausted! :-/")
            pid = os.getpid()
            os.kill(pid, signal.SIGINT)
            return self.zero_chunk
        chunk = np.frombuffer(chunk, dtype=np.int16)
        #try:
        chunk = np.reshape(chunk, (args.frames_per_chunk, args.number_of_channels))
        #except ValueError:
            #logging.warning("Input exhausted! :-/")
            #pid = os.getpid()
            #os.kill(pid, signal.SIGINT)
            #self.input_exhausted = True
        return chunk
            
    def _read_IO_and_play(self, DAC, frames, time, status):
        '''Similar to _record_IO_and_play, but the recorded chunk comes from a file.
        '''
        chunk = self.read_chunk_from_file()
        packed_chunk = self.pack(chunk)
        self.send(packed_chunk)
        try:
            packed_chunk = self.receive()
            chunk = self.unpack(packed_chunk)
        except (socket.timeout, BlockingIOError, ValueError):
            chunk = self.zero_chunk
            logging.debug("playing zero chunk")
        DAC[:] = chunk
        if __debug__:
            print(next(spinner), end='\b', flush=True)
        return chunk

    def mic_stream(self, callback_function):
        '''Creates the stream.

        Returns
        -------
        sounddevice.Stream
           The object that records and plays audio represented in numpy arrays.
        '''
        return sd.Stream(device=(args.input_device, args.output_device),
                         #dtype=self.SAMPLE_TYPE,
                         dtype=np.int16,
                         samplerate=args.frames_per_second,
                         blocksize=args.frames_per_chunk,
                         channels=args.number_of_channels,
                         callback=callback_function)

    def file_stream(self, callback_function):
        '''Creates the stream.

        Returns
        -------
        sounddevice.Stream
           The object that records and plays audio represented in numpy arrays.
        '''
        return sd.OutputStream(
            dtype=np.int16,
            samplerate=args.frames_per_second,
            blocksize=args.frames_per_chunk,
            device=args.output_device,
            channels=args.number_of_channels,
            callback=callback_function)

    def run(self):
        '''Creates the stream, install the callback function, and waits for
        an enter-key pressing.'''
        #self.sock.settimeout(self.chunk_time)
        self.sock.settimeout(0)
        logging.info("Press enter-key to quit")

        with self.stream(self._handler):
            input()
            #while not self.input_exhausted:
            #    time.sleep(1)

    def print_final_averages(self):
        pass

parser.add_argument("--show_stats", action="store_true", help="Shows bandwith, CPU and quality statistics")
parser.add_argument("--show_samples", action="store_true", help="Shows samples values")
parser.add_argument("--show_spectrum", action="store_true", help="Shows Fourier spectrum")

import threading
import pygame  # If fails opening iris and swrast, run "export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6" (good idea to put it into .bashrc)
import pygame_widgets
#import spectrum # If fails (DOLPHINS.WAV not found), update setuptools with "pip install setuptools"

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

    seconds_per_cycle = 1
    
    #def __init__(self, args):
    def __init__(self):
        ''' Defines the stuff for providing running information. '''
        super().__init__()

        #self.args = args

        self.cycle = 1 # An infinite cycle's counter.

        self.sent_bytes_count = 0
        self.received_bytes_count = 0
        self.sent_messages_count = 0
        self.received_messages_count = 0
        self.sent_KBPS = 0
        self.received_KBPS = 0
        # All these counters are reset at the end of each cycle.

        self.average_sent_messages = 0
        self.average_received_messages = 0
        self.average_CPU_usage = 0
        self.average_global_CPU_usage = 0
        self.average_sent_KBPS = 0
        self.average_received_KBPS = 0
        # All average values are per cycle.
        
        self.frames_per_cycle = self.seconds_per_cycle * args.frames_per_second
        self.chunks_per_cycle = self.frames_per_cycle / args.frames_per_chunk

        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]

        self.total_number_of_sent_chunks = 0
        self.chunks_to_sent = 999999
        if args.reading_time:
            self.chunks_to_sent = int(args.reading_time)/self.chunk_time

        logging.info(f"seconds_per_cycle = {self.seconds_per_cycle}")            
        logging.info(f"chunks_per_cycle = {self.chunks_per_cycle}")
        logging.info(f"frames_per_cycle = {self.frames_per_cycle}")
        
        # Queue for communicating with self.update_plot()
        #self.q = queue.Queue()

        if args.show_spectrum:
            self.recorded_chunk = self.generate_zero_chunk()
            self.played_chunk = self.generate_zero_chunk()
            # PyGame stuff
            self.eye_size = args.frames_per_chunk//2
            self.window_heigh = self.eye_size + 1
            pygame.init()
            self.display = pygame.display.set_mode((args.frames_per_chunk//2, self.window_heigh))
            self.display.fill((0, 0, 0))
            self.surface = pygame.surface.Surface((args.frames_per_chunk//2, self.window_heigh)).convert()
            self.RGB_matrix = np.zeros((self.window_heigh, args.frames_per_chunk//2, 3), dtype=np.uint8)
            #self.RGB_matrix = np.zeros((self.window_heigh, 512, 3), dtype=np.uint8)
            #self.eye = 255*np.eye(512, dtype=int)
            self.eye = 255*np.eye(self.eye_size, dtype=int)
            #self.hamming_window = spectrum.window.Window(args.frames_per_chunk, "hamming").data
            self.hamming_window = np.hamming(args.frames_per_chunk)

    def update_display(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                done = True
                break
        le_channel_rec = self.recorded_chunk[:, 0]
        ri_channel_rec = self.recorded_chunk[:, 1]
        le_channel_pla = self.played_chunk[:, 0]
        ri_channel_pla = self.played_chunk[:, 1]
        le_windowed_channel_rec = le_channel_rec * self.hamming_window
        ri_windowed_channel_rec = ri_channel_rec * self.hamming_window
        le_windowed_channel_pla = le_channel_pla * self.hamming_window
        ri_windowed_channel_pla = ri_channel_pla * self.hamming_window
        le_FFT_rec = np.fft.rfft(le_windowed_channel_rec)
        ri_FFT_rec = np.fft.rfft(ri_windowed_channel_rec)
        le_FFT_pla = np.fft.rfft(le_windowed_channel_pla)
        ri_FFT_pla = np.fft.rfft(ri_windowed_channel_pla)
        #le_spectrum = 100*np.log10(np.sqrt(le_FFT.real*le_FFT.real + le_FFT.imag*le_FFT.imag) / args.frames_per_chunk + 1)
        #ri_spectrum = 100*np.log10(np.sqrt(ri_FFT.real*ri_FFT.real + ri_FFT.imag*ri_FFT.imag) / args.frames_per_chunk + 1)
        le_spectrum_rec = np.sqrt(le_FFT_rec.real*le_FFT_rec.real + le_FFT_rec.imag*le_FFT_rec.imag) / args.frames_per_chunk + 1
        ri_spectrum_rec = np.sqrt(ri_FFT_rec.real*ri_FFT_rec.real + ri_FFT_rec.imag*ri_FFT_rec.imag) / args.frames_per_chunk + 1
        le_spectrum_pla = np.sqrt(le_FFT_pla.real*le_FFT_pla.real + le_FFT_pla.imag*le_FFT_pla.imag) / args.frames_per_chunk + 1
        ri_spectrum_pla = np.sqrt(ri_FFT_pla.real*ri_FFT_pla.real + ri_FFT_pla.imag*ri_FFT_pla.imag) / args.frames_per_chunk + 1
        le_spectrum_rec = le_spectrum_rec.astype(np.uint16)
        ri_spectrum_rec = ri_spectrum_rec.astype(np.uint16)
        le_spectrum_pla = le_spectrum_pla.astype(np.uint16)
        ri_spectrum_pla = ri_spectrum_pla.astype(np.uint16)
        #R_matrix = self.eye[(self.recorded_chunk[::4, 0]>>8) + 128]
        #G_matrix = self.eye[(self.recorded_chunk[::4, 1]>>8) + 128]
        #R_matrix = self.eye[np.clip(511 - le_spectrum, 0, 511)]
        #G_matrix = self.eye[np.clip(511 - ri_spectrum, 0, 511)]
        #R_matrix = self.eye[np.clip(self.eye_size-1 - le_spectrum, 0, self.eye_size-1)]
        #G_matrix = self.eye[np.clip(self.eye_size-1 - ri_spectrum, 0, self.eye_size-1)]
        le_spectrum_rec = np.clip(self.eye_size - le_spectrum_rec, 0, self.eye_size-1)
        ri_spectrum_rec = np.clip(self.eye_size - ri_spectrum_rec, 0, self.eye_size-1)
        le_spectrum_pla = np.clip(le_spectrum_pla, 0, self.eye_size-1)
        ri_spectrum_pla = np.clip(ri_spectrum_pla, 0, self.eye_size-1)
        R_matrix = self.eye[le_spectrum_rec]
        G_matrix = self.eye[ri_spectrum_rec]
        R_matrix += self.eye[le_spectrum_pla]
        G_matrix += self.eye[ri_spectrum_pla]
        self.RGB_matrix[:, :, 0] = R_matrix
        self.RGB_matrix[:, :, 1] = G_matrix
        #self.RGB_matrix[0:R_matrix.shape[0], 0:R_matrix.shape[1], 0] = R_matrix
        #self.RGB_matrix[0:G_matrix.shape[0], 0:G_matrix.shape[1], 0] = G_matrix
        surface = pygame.surfarray.make_surface(self.RGB_matrix)
        #surf = pygame.surfarray.blit_array(self.surface, self.recorded_chunk[:,0])
        #for i in range(256):
        #    self.display.set_at((i, self.recorded_chunk[i][0] + 128), (255, 0, 0))
        #    self.display.set_at((i, self.recorded_chunk[i][1] + 128), (0, 0, 255))
        self.display.blit(surface, (0, 0))
        #pygame.surfarray.blit_array(self.surface, (0, 0))
        pygame_widgets.update(events)
        pygame.display.update()

    def send(self, packed_chunk):
        ''' Computes the number of sent bytes and the number of sent packets. '''
        super().send(packed_chunk)
        #self.sent_bytes_count += len(packed_chunk)*np.dtype(self.SAMPLE_TYPE).itemsize*args.number_of_channels
        self.sent_bytes_count += packed_chunk.nbytes  # Returns the number of bytes of the numpy array packed_chunk
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

    def stats(self):
        string = ""
        string += "{:5d}".format(self.cycle)
        string += "{:8d}".format(self.sent_messages_count)
        string += "{:8d}".format(self.received_messages_count)
        string += "{:8d}".format(self.sent_KBPS)
        string += "{:8d}".format(self.received_KBPS)
        string += "{:5d}".format(int(self.CPU_usage))
        string += "{:5d}".format(int(self.global_CPU_usage))
        return string

    def print_stats(self):
        print(self.stats())

    def first_line(self):
        string = ""
        string += "{:5s}".format('') # cycle
        string += "{:>8s}".format("sent") # sent_messages_count
        string += "{:>8s}".format("recv.") # received_messages_count
        string += "{:>8s}".format("sent") # sent_KBPS
        string += "{:>9s}".format("recv.") # received_KBPS
        string += "{:3s}".format('') # CPU_usage
        string += "{:>6s}".format("Global") # average_global_CPU_usage
        return string

    def print_first_line(self):
        print(self.first_line())

    def second_line(self):
        string = ""
        string += "{:5s}".format("cycle") # cycle
        string += "{:>8s}".format("mesgs.") # sent_messages_count
        string += "{:>8s}".format("mesgs.") # received_messages_count
        string += "{:>8s}".format("KBPS") # sent_KBPS
        string += "{:>8s}".format("KBPS") # received_KBPS
        string += "{:>5s}".format("%CPU") # CPU_usage
        string += "{:>5s}".format("%CPU") # global_CPU_usage
        return string

    def print_second_line(self):
        print(self.second_line())

    def averages(self):
        string = ""
        string += "{:5s}".format("Avgs:") # cycle
        string += "{:8d}".format(int(self.average_sent_messages))
        string += "{:8d}".format(int(self.average_received_messages))
        string += "{:>8d}".format(int(self.average_sent_KBPS))
        string += "{:>8d}".format(int(self.average_received_KBPS))
        string += "{:>5d}".format(int(self.average_CPU_usage))
        string += "{:>5d}".format(int(self.average_global_CPU_usage))
        return string

    def print_averages(self):
        print("\033[7m" + self.averages() + "\033[m")
        
    def separator(self):
        string = ""
        string += f"{'='*(5*3+8*4)}"
        return string

    def print_separator(self):
        print(self.separator())

    def print_header(self):
        self.print_first_line()
        self.print_second_line()
        self.print_separator()

    def print_trailer(self):
        self.print_second_line()
        self.print_first_line()
        
    # https://en.wikipedia.org/wiki/Moving_average
    def moving_average(self, average, new_sample, number_of_samples):
        return average + (new_sample - average) / number_of_samples

    def cycle_feedback(self):
        ''' Computes and shows the statistics. '''

        elapsed_time = time.time() - self.old_time
        elapsed_CPU_time = psutil.Process().cpu_times()[0] - self.old_CPU_time
        self.CPU_usage = 100 * elapsed_CPU_time / elapsed_time
        self.global_CPU_usage = psutil.cpu_percent()
        self.average_CPU_usage = self.moving_average(self.average_CPU_usage, self.CPU_usage, self.cycle)
        self.average_global_CPU_usage = self.moving_average(self.average_global_CPU_usage, self.global_CPU_usage, self.cycle)
        self.old_time = time.time()
        self.old_CPU_time = psutil.Process().cpu_times()[0]

        self.average_sent_messages = self.moving_average(self.average_sent_messages, self.sent_messages_count, self.cycle)
        self.average_received_messages = self.moving_average(self.average_received_messages, self.received_messages_count, self.cycle)

        self.sent_KBPS = int(self.sent_bytes_count * 8 / 1000 / elapsed_time)
        self.received_KBPS = int(self.received_bytes_count * 8 / 1000 / elapsed_time)
        self.average_sent_KBPS = self.moving_average(self.average_sent_KBPS, self.sent_KBPS, self.cycle)
        self.average_received_KBPS = self.moving_average(self.average_received_KBPS, self.received_KBPS, self.cycle)

        self.print_stats()
        self.print_averages()
        self.print_separator()        
        self.print_trailer()
        print("\033[5A")

        self.total_number_of_sent_chunks += self.sent_messages_count
        self.sent_bytes_count = 0
        self.received_bytes_count = 0
        self.sent_messages_count = 0
        self.received_messages_count = 0

        self.cycle += 1

    def print_final_averages(self):
        print('\n'*4)
        print(f"CPU usage average = {self.average_CPU_usage} %")
        print(f"Payload sent average = {self.average_sent_KBPS} kilo bits per second")
        print(f"Payload received average = {self.average_received_KBPS} kilo bits per second")

    def print_running_info(self):
        print("\nInterCom parameters:\n")
        print(args)
        print("\nUsing device:\n")
        print(sd.query_devices(args.input_device))
        print()
        print("Use CTRL+C to quit")

    def show_data(self, data):
        for i in range(4):
            print(data[i], end=' ')
        print("...", end=' ')
        for i in range(args.frames_per_chunk//2 - 2, args.frames_per_chunk//2 + 2):
            print(data[i], end=' ')
        print("...", end=' ')
        for i in range(args.frames_per_chunk-4, args.frames_per_chunk):
            print(data[i], end=' ')

    def show_recorded_chunk(self, recorded_chunk):
        print("I =", end=' ')
        self.show_data(recorded_chunk)
        print()

    def show_played_chunk(self, played_chunk):
        print("\033[7mO =", end=' ')
        self.show_data(played_chunk)
        print("\033[m")

    def __unpack(self, packed_chunk):
        chunk = super().unpack(packed_chunk)
        self.played_chunk = chunk
        return chunk

    def _record_IO_and_play(self, ADC, DAC, frames, time, status):
        # Notice that in each call to this method, a (different) chunk is processed.

        if args.show_samples:
            self.show_recorded_chunk(ADC)

        super()._record_IO_and_play(ADC, DAC, frames, time, status)

        if args.show_samples:
            self.show_played_chunk(DAC)

        #self.q.put(DAC[:128])
        self.recorded_chunk = ADC
        self.played_chunk = DAC
        #print(".")

    def _read_IO_and_play(self, DAC, frames, time, status):
        chunk = super()._read_IO_and_play(DAC, frames, time, status)

        if args.show_samples:
            self.show_recorded_chunk(chunk)
            self.show_played_chunk(DAC)

        self.recorded_chunk = DAC
        self.played_chunk = DAC

    def loop_update_display(self):
        while True:
            time.sleep(0.1)
            self.update_display()

    def loop_cycle_feedback(self):
        while self.total_number_of_sent_chunks < self.chunks_to_sent:# and not self.input_exhausted:
            time.sleep(self.seconds_per_cycle)
            self.cycle_feedback()

    def run(self):
        cycle_feedback_thread = threading.Thread(target=self.loop_cycle_feedback)
        cycle_feedback_thread.daemon = True
        self.sock.settimeout(0)
        self.print_running_info()
        self.print_header()
        with self.stream(self._handler):
            cycle_feedback_thread.start()
            #if self.args.show_spectrum:
            if args.show_spectrum:
                self.loop_update_display()
            else:
                input()

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    parser.description = __doc__
    try:
        argcomplete.autocomplete(parser)
    except Exception:
        logging.warning("argcomplete not working :-/")
    args = parser.parse_known_args()[0]

    if args.list_devices:
        print("Available devices:")
        print(sd.query_devices())
        quit()

    if args.show_stats or args.show_samples or args.show_spectrum:
        #intercom = Minimal__verbose(args)
        intercom = Minimal__verbose()
    else:
        intercom = Minimal()

    try:
        intercom.run()
    except KeyboardInterrupt:
        parser.exit("\nSIGINT received")
    finally:
        intercom.print_final_averages()
