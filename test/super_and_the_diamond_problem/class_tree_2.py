# Minimal ---> Minimal_V
#    |            |
#    v            v
# Buffer  ---> Buffer_V

class Minimal:
    def __init__(self):
        print("Minimal")

class Minimal_V(Minimal):
    def __init__(self):
        super().__init__()
        print("Minimal_V")
        
class Buffer(Minimal):
    def __init__(self):
        super().__init__()
        print("Buffer")

class Buffer_V(Buffer, Minimal_V):
    def __init__(self):
        super().__init__()
        print("Buffer_V")

b_v = Buffer_V()
print(":-) Constructors are called in the right order")

print("Method Resolution Order:")
print(Buffer_V.__mro__)
