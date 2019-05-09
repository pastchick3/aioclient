from ..client.client import Client
from ..client.request import Request
from ..interpreter import Interpreter
from .asynctest import AsyncTest


class TestEvaluator(AsyncTest):

    @AsyncTest.asynchronize
    async def test_single(self):
        source = '''
            get from 'https://www.baidu.com/'
        '''

        expected_result = Request('https://www.baidu.com/')

        try:
            interpreter = Interpreter(Client())
            result = await interpreter.run(source)
            self.assertEqual(result, expected_result)
        finally:
            await interpreter.close()

    @AsyncTest.asynchronize
    async def test_context(self):
        source = '''
            get from 'https://www.baidu.com/'
        '''

        expected_result = Request('https://www.baidu.com/')

        async with Interpreter() as interpreter:
            result = await interpreter.run(source)
            self.assertEqual(result, expected_result)
