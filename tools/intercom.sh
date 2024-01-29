#!/bin/bash

intercom=intercom_odwt
frames_per_chunk=1024
frames_per_second=44100
number_of_channels=2
my_port=4444
destination_port=4444
destination_address=localhost

__debug__=0

usage() {
    echo $0
    echo "Real-time Autio Intercommunicator"
    echo "  intercom=$intercom"
    echo "  [-s frames (stereo or mono samples) per chunk ($frames_per_chunk)]"
    echo "  [-r frames per second ($frames_per_second)]"
    echo "  [-c number of channels ($number_of_channels)]"
    echo "  [-p my I/O port ($my_port)]"
    echo "  [-i interlocutor's I/O port ($destination_port)]"
    echo "  [-a interlocutor's IP-address/host-name ($destination_address)]"
    echo "  [-? (help)]"
}

if [ $__debug__ -eq 1 ]; then
    (echo $0 $@ 1>&2)
fi

while getopts "s:r:c:p:i:a:?h" opt; do
    case ${opt} in
        s)
            frames_per_chunk="${OPTARG}"
            if [ $__debug__ = 1 ]; then
                echo $0: frames_per_chunk=$frames_per_chunk
            fi
            ;;
        r)
            frames_per_second="${OPTARG}"
            if [ $__debug__ = 1 ]; then
                echo $0: frames_per_second=$frames_per_second
            fi
            ;;
        c)
            number_of_channels="${OPTARG}"
            if [ $__debug__ = 1 ]; then
                echo $0: number_of_channels=$number_of_channels
            fi
            ;;
        p)
            my_port="${OPTARG}"
            if [ $__debug__ = 1 ]; then
                echo $0: my_port=$my_port
            fi
            ;;
        i)
            destination_port="${OPTARG}"
            if [ $__debug__ = 1 ]; then
                echo $0: destination_port=$destination_port
            fi
            ;;
        a)
            destination_address="${OPTARG}"
            if [ $__debug__ = 1 ]; then
                echo $0: destination_address=$destination_address
            fi
            ;;
        ? | h)
            usage
            exit 0
            ;;
        \?)
            echo $0: "Invalid option: -${OPTARG}" >&2
            usage
            exit 1
            ;;
        :)
            echo $0: "Option -${OPTARG} requires an argument." >&2
            usage
            exit 1
            ;;
    esac
done

command="nice -n 0 python3 $intercom.py --frames_per_chunk=$frames_per_chunk --frames_per_second=$frames_per_second --number_of_channels=$number_of_channels --my_port=$my_port --destination_port=$destination_port --destination_address=$destination_address"

if [ $__debug__ = 1 ]; then
  echo $0: command
fi

´command´
