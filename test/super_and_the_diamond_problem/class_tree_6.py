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
        super().pack()
        print("Buffer's pack")

class Buffer_V(Buffer, Minimal_V):
    def __init__(self):
        super().__init__()

    def pack(self):
        Buffer.pack(self)
        print("Buffer_V's pack")

b = Buffer()
b.pack()
print(":-)")
print()
b = Buffer_V()
b.pack()
print(":-! Surprise! Minimal_V.pack() is called by Buffer.pack() (this option is also valid for InterCom)")
