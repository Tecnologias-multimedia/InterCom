# Minimal ---> Minimal_V
#    |            |
#    v            v
# Buffer  ---> Buffer_V

class Minimal:
    def __init__(self):
        print("Minimal")

class Minimal_V(Minimal):
    def __init__(self):
        print("Minimal_V")
        
class Buffer(Minimal):
    def __init__(self):
        print("Buffer")

class Buffer_V(Buffer, Minimal_V):
    def __init__(self):
        print("Buffer_V")

b_v = Buffer_V()
print(":-/ Constructors aren't called")

print("Method Resolution Order:")
print(Buffer_V.__mro__)

