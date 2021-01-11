#!/bin/bash

# Uninstall the virtual microphone.

pactl unload-module module-pipe-source
rm /home/ana/.config/pulse/client.conf
