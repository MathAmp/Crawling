from time import time

url = 'http://sugang.snu.ac.kr/sugang/cc/cc100.action'


def timer(func):

    def wrapper(*args, **kwargs):
        start = time()
        func(*args, **kwargs)
        end = time()
        print(f"{func.__name__} is executed in {end - start}s")
        return end - start

    return wrapper


