#! /bin/bash

sudo -S tc qdisc delete dev lo root netem delay 43.75ms 6.88ms 0.375% distribution normal
tc qdisc show dev lo 
