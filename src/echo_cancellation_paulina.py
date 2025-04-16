#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Echo cancellation (template) with artificial signal.'''

import logging
import numpy as np

import minimal
import buffer


class Echo_Cancellation(buffer.Buffering):
    def __init__(self, delay_samples=5, rtt_average=150, attenuation=1.0):
        """
        A class inheriting from Buffering, implementing the delay-and-subtract solution.

        delay_samples: Delay in samples (estimated as d).
        rtt_average: Average RTT time in milliseconds.
        attenuation: Attenuation factor for the echo signal.
        """
        super().__init__()
        self.delay_samples = delay_samples
        self.rtt_average = rtt_average
        self.attenuation = attenuation
        self.processed_chunks = 0  # Counter for processed chunks
        self.total_rtt = 0  # Total sum of estimated RTTs
        self.chunk_number = 0  # Initialize chunk counter
        self.CHUNK_NUMBERS = 10  # Set a limit for chunk numbers
        logging.info(__doc__)

    def estimate_rtt(self, timestamps):
        """
        Function to estimate RTT (Round-Trip Time).
        timestamps: List of pairs (send_time, receive_time) in milliseconds.
        """
        rtts = [recv_time - send_time for send_time, recv_time in timestamps]
        avg_rtt = sum(rtts) / len(rtts)  # Calculate average RTT
        self.total_rtt += avg_rtt
        self.processed_chunks += 1
        return avg_rtt

    def subtract_echo(self, mixed_signal):
        """
        Removes echo using the delay-and-subtract method.
        """
        # Create a delayed signal
        delayed_signal = np.roll(mixed_signal, self.delay_samples)
        # Remove echo based on the equation (4)
        echo_canceled_signal = mixed_signal - self.attenuation * delayed_signal
        # Zero out shifted parts
        echo_canceled_signal[:self.delay_samples] = mixed_signal[:self.delay_samples]
        return echo_canceled_signal

    def _generate_fake_audio(self, sample_rate=44100, duration=1.0, frequency=440):
        """
        Generates a fake sine wave signal to simulate audio input.
        """
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        return np.sin(2 * np.pi * frequency * t)

    def _record_io_and_play(self, indata, outdata, frames, time, status):
        """
        Override method to record, process, and play audio.
        Instead of recording, it uses simulated data.
        """
        # Generate fake audio input (sine wave)
        fake_audio = self._generate_fake_audio()
        # Mix fake_audio with some noise (for testing echo cancellation)
        mixed_signal = fake_audio + np.random.normal(0, 0.1, fake_audio.shape)

        # Process the signal to cancel the echo
        processed_chunk = self.subtract_echo(mixed_signal)

        # Output processed signal
        outdata[:] = np.expand_dims(processed_chunk[:frames], axis=-1)

        logging.debug(f"Processed chunk: {processed_chunk[:10]}...")  # Show a small part of the processed chunk for debugging


class Echo_Cancellation__verbose(Echo_Cancellation, buffer.Buffering__verbose):
    def __init__(self, delay_samples=5, rtt_average=150, attenuation=1.0):
        super().__init__(delay_samples, rtt_average, attenuation)


try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Enable detailed logging for debugging
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working  ~U")
    minimal.args = minimal.parser.parse_known_args()[0]

    # Determine which version of the Echo_Cancellation class to use
    if minimal.args.show_stats or minimal.args.show_samples or minimal.args.show_spectrum:
        intercom = Echo_Cancellation__verbose()
    else:
        intercom = Echo_Cancellation()
    try:
        intercom.run()  # Start processing
    except KeyboardInterrupt:
        minimal.parser.exit("\nSIGINT received")


