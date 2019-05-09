import asyncio
import unittest
from functools import wraps


class AsyncTest(unittest.TestCase):

    @classmethod
    def asynchronize(cls, func):
        @wraps(func)
        def wrapper(self):
            return asyncio.run(func(self))
        return wrapper
