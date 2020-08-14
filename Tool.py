from time import time


def timer(func):

    def wrapper(*args, **kwargs):
        start = time()
        func(*args, **kwargs)
        end = time()
        print(f"{func.__name__} is executed in {end - start}s")
        return end - start

    return wrapper


