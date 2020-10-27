import socket

class UdpSender():
    def __enter__(self):
        """Create an UDP socket."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("socket created")
        return self

    def send(self, packed_chunk, out_port, destination):
        """Send data."""
        self.sock.sendto(packed_chunk, (destination, out_port))

    def __exit__(self,ext_type,exc_value,traceback):
        """Close the socket."""
        self.sock.close()
        print("socket closed")