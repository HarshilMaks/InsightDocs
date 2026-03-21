import limits
print(dir(limits))
try:
    from limits import Limiter
    print("Found Limiter")
except ImportError:
    print("Limiter not found in top level")
