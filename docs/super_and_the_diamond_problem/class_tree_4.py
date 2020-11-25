# Minimal ---> Minimal_V
#    |            |
#    v            v
# Buffer  ---> Buffer_V

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

b = Buffer()
b.pack()
print("Thats OK :-)")
print()
b = Buffer_V()
b.pack()
print(":-) Everything seems to be OK, if we want all pack()'s to be run (this is what we want in InterCom)")
