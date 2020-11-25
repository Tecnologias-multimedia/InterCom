import socket

class UdpReceiver():
    # We use a context manager (https://docs.python.org/3/reference/datamodel.html#context-managers).
    def __init__(self, in_port):
        self.in_port = in_port

    def __enter__(self):
        """Create an UDP socket and listen to it."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("socket created")
        self.sock.bind(('', self.in_port))
        print(f"listening at {self.sock.getsockname()} ... ")
        return self

    def receive(self, payload_size):
        """Receive a datagram."""
        (packed_chunk, _) = self.sock.recvfrom(payload_size)
        return packed_chunk
    
    def __exit__(self,ext_type,exc_value,traceback):
        """Close the socket."""
        self.sock.close()
        print("socket closed")