#!/bin/bash

# Uninstall the virtual microphone.

pactl unload-module module-pipe-source
rm $HOME/.config/pulse/client.conf
