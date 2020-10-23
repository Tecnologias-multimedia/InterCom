import select, numpy as np, curses, socket, curses.textpad, sounddevice as sd

# Constants
TXT = 0
FNC = 1

KEY_J = 106
KEY_K = 107

# Default IP
UDP_REMOTE_IP = "127.0.0.1"

# Default port
UDP_PORT = 4444

BLOCK_SIZE = 2048
UDP_BUFFER = BLOCK_SIZE ** 2

sock = socket.socket(socket.AF_INET, # Internet
                    socket.SOCK_DGRAM) # UDP

# Callback used when Stream reaches the specified block size
def connect_cb(indata, outdata, frames, time, status):

    """ SENDING DATA """
    sock.sendto(indata, (UDP_REMOTE_IP, UDP_PORT))

    """ RECEIVING DATA """
    # Check if socket has data to read
    # We ignore writable sockets 'cause
    # we only care about readable sockets
    readable, [], [] = select.select([sock], [], [], 0)

    if len(readable):
        # Receive from socket
        data, address = sock.recvfrom(UDP_BUFFER)
        # Convert to array from buffer
        data = np.frombuffer(data, dtype='int16')
        # Reshape from 1D array to 2D
        data = np.reshape(data, (-1, 2))
        # Output data to speaker
        outdata[:] = data
    else:
        # If no data is received, we have to fill the output with 0's
        outdata.fill(0)


def connect_fn(stdscr):

    global UDP_REMOTE_IP

    # We get the height and width
    h, w = stdscr.getmaxyx()

    # We position the text at the bottom
    text = "IP Address (without port): "
    stdscr.addstr(h - 2, 1, text)

    # We allow the user to type on screen
    curses.echo()
    # and get their input
    UDP_REMOTE_IP = stdscr.getstr(h - 2, len(text)+1).decode(encoding="utf-8")
    curses.noecho()

    stdscr.clear()

    if len(UDP_REMOTE_IP) == 0:
        return

    # We start sending and receiving audio packets
    with sd.Stream(samplerate=44100, channels=2, dtype='int16', 
                    blocksize=BLOCK_SIZE, callback=connect_cb):
        text = "Sending UDP packets to " + UDP_REMOTE_IP
        h, w = stdscr.getmaxyx()
        x = w//2 - len(text)//2
        y = h//2
        stdscr.addstr(y, x, text)
        stdscr.refresh()
        stdscr.getch()

# Exit function
def exit_fn(stdscr):
    # Clean up stuff
    stdscr.clear()
    sock.close()
    exit(0)


# In this array we store buttons with
# their respective function
menu = [
    ['Connect', connect_fn],
    ['Exit', exit_fn]
]


# Function we use to draw the main menu
def print_menu(stdscr, selected_entry):

    global UDP_LOCAL_PORT

    stdscr.clear()
    height, width = stdscr.getmaxyx()

    hostname = socket.gethostname()    
    host_ip = socket.gethostbyname(hostname) 

    text = hostname + " hosting with IP: " + host_ip + ":" + str(UDP_PORT)

    x = width//2 - len(text)//2

    stdscr.addstr(1, x, text)

    for idx, entry in enumerate(menu):
        x = width//2 - len(entry[TXT])//2
        y = height//2 - len(menu)//2 + idx
        if idx == selected_entry:
            stdscr.addstr(y, x-2, '→ ' + entry[TXT] + ' ←')
        else:
            stdscr.addstr(y, x, entry[TXT])
    stdscr.refresh()

def main(stdscr):

    # turn off cursor blinking
    curses.curs_set(0)

    # color scheme for selected row
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # specify the current selected row
    current_entry = 0

    # We dont need this since we are not using the try/except approach
    # sock.setblocking(0)

    # Bind the socket to the default port (4444)
    sock.bind(('', UDP_PORT))

    # print the menu
    print_menu(stdscr, current_entry)

    # We get the users input and decide what to do
    while True:
        key = stdscr.getch()

        if key in [curses.KEY_UP, KEY_K]:
            current_entry -= (current_entry > 0)
        elif key in [curses.KEY_DOWN, KEY_J]:
            current_entry += (current_entry < len(menu)-1)
        elif key in [curses.KEY_ENTER, 10, 13]:
            menu[current_entry][FNC](stdscr)

        print_menu(stdscr, current_entry)


curses.wrapper(main)
