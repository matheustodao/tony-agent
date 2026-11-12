import time
from functools import wraps

def profiling(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()

        result = func(*args, **kwargs)

        elapsed = time.perf_counter() - start

        print('\n\n=======')
        print(f'Function name: {func.__name__}')
        print(f'Elapsed time: {elapsed:.4f}s')
        print('\n\n=======')

        return result
    return wrapper
