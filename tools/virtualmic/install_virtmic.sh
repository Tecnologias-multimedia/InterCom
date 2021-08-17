#!/bin/bash

# This script will create a virtual microphone for PulseAudio to use and set it as the default device.

# Load the "module-pipe-source" module to read audio data from a FIFO special file.
echo "Creating virtual microphone."
pactl load-module module-pipe-source source_name=virtmic file=/tmp/virtmic format=s16le rate=44100 channels=2

# Set the virtmic as the default source device.
echo "Set the virtual microphone as the default device."
pactl set-default-source virtmic

# Create a file that will set the default source device to virtmic for all PulseAudio client applications.
echo "default-source = virtmic" > $HOME/.config/pulse/client.conf

# Write the audio file to the named pipe virtmic. This will block until the named pipe is read.
echo "Writing audio file to virtual microphone."
#cat $1 > /tmp/virtmic
while true; do
    echo -n "."
    cat $1 > /tmp/virtmic
done
