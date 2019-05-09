from ..client.client import Client
from ..client.request import HTTPMethod, Request
from ..interpreter.evaluator import Evaluator
from ..interpreter.lexer import Lexer
from ..interpreter.parser import Parser
from .asynctest import AsyncTest


class TestEvaluator(AsyncTest):

    @AsyncTest.asynchronize
    async def test_single(self):
        source = '''
            let request = get from 'http://www.baidu.com/s' with
                            set wd equals 'BNF' in query

            let future = send request

            let response = wait future

            process response as html with {{
                return obj.xpath('//title')[0].text
            }}
        '''

        expected_result = 'BNF_百度搜索'

        client = Client()
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            program = parser.parse()
            evaluator = Evaluator(client)
            result = await evaluator.eval(program)
            self.assertEqual(result, expected_result)
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_multiple(self):
        source = '''
            let request = get from [
                'http://www.baidu.com/',
                'https://www.douban.com/',
            ]

            let future = send request
            
            let responses = wait future

            process responses as html with {{
                return obj.xpath('//title')[0].text
            }}
        '''

        expected_result = [
            '百度一下，你就知道',
            '豆瓣',
        ]

        client = Client()
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            program = parser.parse()
            evaluator = Evaluator(client)
            result = await evaluator.eval(program)
            self.assertEqual(result, expected_result)
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_implicit(self):
        url = 'http://www.baidu.com/s'
        source = '''
            url
            then get from with
                    set wd equals 'BNF' in query
            then send
            then wait
            then process as html with {{
                return obj.xpath('//title')[0].text
            }}
        '''

        expected_result = 'BNF_百度搜索'

        client = Client()
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            program = parser.parse()
            evaluator = Evaluator(client)
            result = await evaluator.eval(program, global_env=locals())
            self.assertEqual(result, expected_result)
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_request_expr(self):
        source = '''
            post to 'http://www.baidu.com/s' with
                timeout 5 minutes
                retry 3 times at 1 minute apart
                sleep 1 second per request
                set wd equals 'BNF' in query
                set UA equals 'Chrome' in headers
                set json equals {'k': 'v'} in body
                set id equals 1 in meta
        '''

        expected_result = Request(
            url='http://www.baidu.com/s',
            method=HTTPMethod.POST,
            timeout=300,
            retry=3,
            retry_interval=60,
            sleep=1,
            headers={'UA': 'Chrome'},
            params={'wd': 'BNF'},
            json={'k': 'v'},
            meta={'id': 1},
        )

        client = Client()
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            program = parser.parse()
            evaluator = Evaluator(client)
            result = await evaluator.eval(program)
            self.assertEqual(result, expected_result)
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_result_expr(self):
        source = '''
            let request = get from [
                'https://www.google.com/',
                'https://www.baidu.com/',
                'https://www.baidu.com/s?wd=1',
                'https://httpbin.org/get',
                'https://movie.douban.com/',
            ]

            let future = send request
            
            let responses = wait future

            process responses
                whose status does not equal 200 as bytes with {{
                    return obj + b" bytes"
                }}
                whose url equals 'https://www.baidu.com/' as str with {{
                    return obj[0] + " str"
                }}
                whose url contains 'wd=1' as html with {{
                    return obj.xpath('//title')[0].text + " html"
                }}
                whose url does not contain '.com' as json with extract_url
                otherwise as xml with extract_title
        '''

        def extract_url(response, obj):
            return str(response.url) + " json"

        def extract_title(response, obj):
            return obj.xpath('//title')[0].text + ' xml'

        expected_result = [
            b' bytes',
            '< str',
            '1_百度搜索 html',
            'https://httpbin.org/get json',
        ]

        client = Client()
        try:
            lexer = Lexer(source)
            parser = Parser(lexer)
            program = parser.parse()
            evaluator = Evaluator(client)
            result = await evaluator.eval(program, local_env=locals())
            self.assertEqual(result[:4], expected_result)
            self.assertTrue(isinstance(result[4], Exception))
        finally:
            await client.close()
