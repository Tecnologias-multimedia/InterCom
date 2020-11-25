#! /bin/bash

sudo -S tc qdisc delete dev lo root handle 1: tbf rate $bitrate.0kbit burst 32kbit limit 32kbit
sudo -S tc qdisc delete dev lo parent 1:1 handle 10: netem delay 43.75ms 6.88ms 0.375% distribution normal
tc qdisc show dev lo 
