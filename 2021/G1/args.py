import argparse

def get_args():
    # Audio defaults
    # 1 = mono, 2 = stereo
    NUMBER_OF_CHANNELS = 2
    FRAMES_PER_SECOND  = 44100
    FRAMES_PER_CHUNK   = 1024
    
    # Network defaults
    PAYLOAD_SIZE = 10240
    IN_PORT     = 4444
    OUT_PORT    = 4444
    ADDRESS     = 'localhost'
    N           = 41
    WAVELET     = "db20"
    LEVELS       = 5

    parser = argparse.ArgumentParser(description="Real-Time Audio Intercommunicator",
                                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-f", "--frames_per_chunk",
                        help="Number of frames (stereo samples) per chunk.",
                        type=int, default=FRAMES_PER_CHUNK)
    parser.add_argument("-r", "--frames_per_second",
                        help="Sampling rate in frames/second.",
                        type=int, default=FRAMES_PER_SECOND)
    parser.add_argument("-c", "--number_of_channels",
                        help="Number of channels.",
                        type=int, default=NUMBER_OF_CHANNELS)
    parser.add_argument("-p", "--in_port",
                        help="My listening port.",
                        type=int, default=IN_PORT)
    parser.add_argument("-i", "--out_port",
                        help="Interlocutor's listening port.",
                        type=int, default=OUT_PORT)
    parser.add_argument("-a", "--address",
                        help="Interlocutor's IP address or name.",
                        type=str, default=ADDRESS)
    parser.add_argument("-o", "--payload_size",
                        help="Paiload size.",
                        type=int, default=PAYLOAD_SIZE)
    parser.add_argument("-n", "--buffer_size",
                        help="Buffer size.",
                        type=int, default=N)
    parser.add_argument("-w", "--wavelet_name",
                        help="Wavelet name.",
                        type=str, default=WAVELET)
    parser.add_argument("-l", "--levels",
                        help="Level.",
                        type=int, default=LEVELS)
                                       
    return parser


def show_args(args):
    print("NUMBER OF CHANNELS:", args.number_of_channels)
    print("FRAMES PER SECOND:", args.frames_per_second)
    print("FRAMES PER CHUNK:", args.frames_per_chunk)
    print("PAYLOAD SIZE:", args.payload_size)
    print("IN PORT:", args.in_port)
    print("OUT PORT:", args.out_port)
    print("ADDRESS:", args.address)
    print("N:", args.buffer_size)