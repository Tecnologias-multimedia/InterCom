# Minimal ------> Minimal_V 
#    |               |
#    v               v
# Buffer  ------> Buffer_V
#    |               |
#    v               v
# Compression --> Compression_V

class Minimal:
    def __init__(self):
        pass

    def pack(self):
        print("Minimal's pack")

class Minimal_V(Minimal):
    def __init__(self):
        super().__init__()

    def pack(self):
        super().pack()
        print("Minimal_V's pack")

class Buffer(Minimal):
    def __init__(self):
        super().__init__()

    def pack(self):
        print("Buffer's pack")
        super().pack()

class Buffer_V(Buffer, Minimal_V):
    def __init__(self):
        super().__init__()

    def pack(self):
        super().pack()
        print("Buffer_V's pack")

class Compression(Buffer):
    def __init__(self):
        super().__init__()

    def pack(self):
        print("Compression's pack")
        super().pack()

class Compression_V(Compression, Buffer_V):
    def __init__(self):
        super().__init__()

    def pack(self):
        super().pack()
        print("Compression_V's pack")

b = Compression()
b.pack()
print("Thats OK :-)")
print()
b = Compression_V()
b.pack()
print(":-) Everything seems to be OK, if we want all pack()'s to be run (this is what we want in InterCom)")
