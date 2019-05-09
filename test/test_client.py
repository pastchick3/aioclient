import asyncio
import logging
import os
from time import time

from yarl import URL

from ..client.client import Client
from ..client.request import HTTPMethod, Request
from .asynctest import AsyncTest


class TestClient(AsyncTest):

    @classmethod
    def setUpClass(cls):
        logger = logging.getLogger('client')
        if not logger.hasHandlers():
            logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
            sh = logging.StreamHandler()
            sh.setLevel(logging.DEBUG)
            sh.setFormatter(formatter)
            logger.addHandler(sh)

    @AsyncTest.asynchronize
    async def test_basic(self):
        setting = {
            'headers': {'global-headers': 'global_headers_value'},
            'cookies': {'global_cookies': 'global_cookies_value'},
        }
        client = Client(setting)
        self.assertEqual(repr(client), '<Client - Pending: 0 (0 batch) Processing: 0/0>')
        req = Request(
            url='http://www.httpbin.org/post',
            method=HTTPMethod.POST,
            headers={'headers': 'headers_value'},
            params={'params': 'params_value'},
            meta={'k': 'v'},
        )
        try:
            resp = await client.submit(req)
            assert resp.status == 200
            self.assertEqual(resp.url, URL('http://www.httpbin.org/post?params=params_value'))
            self.assertEqual(resp.json()['headers']['Global-Headers'], 'global_headers_value')
            self.assertEqual(resp.json()['headers']['Headers'], 'headers_value')
            self.assertEqual(resp.json()['headers']['Cookie'], 'global_cookies=global_cookies_value')
            self.assertEqual(resp.meta, {'k': 'v'})
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_request_body(self):
        client = Client()
        try:
            req = Request(
                url='http://www.httpbin.org/post',
                method=HTTPMethod.POST,
                json={'k': 'v'},
            )
            resp = await client.submit(req)
            assert resp.status == 200
            self.assertEqual(resp.json()['json'], {'k': 'v'})

            req = Request(
                url='http://www.httpbin.org/post',
                method=HTTPMethod.POST,
                form={'k': 'v'},
            )
            resp = await client.submit(req)
            assert resp.status == 200
            self.assertEqual(resp.json()['form'], {'k': 'v'})

            req = Request(
                url='http://www.httpbin.org/post',
                method=HTTPMethod.POST,
                body=b'body',
            )
            resp = await client.submit(req)
            assert resp.status == 200
            self.assertEqual(resp.json()['data'], 'body')
            self.assertEqual(resp.json()['headers']['Content-Type'], 'application/octet-stream')

            req = Request(
                url='http://www.httpbin.org/post',
                method=HTTPMethod.POST,
                text='text',
            )
            resp = await client.submit(req)
            assert resp.status == 200
            self.assertEqual(resp.json()['data'], 'text')
            self.assertEqual(resp.json()['headers']['Content-Type'], 'text/plain; charset=utf-8')

            with open('./.t', 'wb') as file:
                file.write(b'file')
            req = Request(
                url='http://www.httpbin.org/post',
                method=HTTPMethod.POST,
                file='./.t',
            )
            resp = await client.submit(req)
            assert resp.status == 200
            self.assertEqual(resp.json()['data'], 'file')
            self.assertEqual(resp.json()['headers']['Content-Type'], 'application/octet-stream')
            self.assertEqual(resp.json()['headers']['Transfer-Encoding'], 'chunked')
            os.remove('./.t')
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_timeout(self):
        req = Request(
            url='https://www.google.com',
            timeout=2,
            retry=1,
            retry_interval=1,
            sleep=2,
        )
        try:
            client = Client()
            start = time()
            resp = await client.submit(req)
            finish = time()
            self.assertTrue(5 < finish - start < 10)
            self.assertEqual(resp.status, -1)
            self.assertIn("TimeoutError('2s'", resp.reason)
            self.assertEqual(resp.content, b'')
        finally:
            await client.close()

    @AsyncTest.asynchronize
    async def test_concurrency(self):
        baidu_urls = [f'https://www.baidu.com/s?wd={i}' for i in range(5)]
        douban_urls = [f'https://movie.douban.com/top250?start={i}&filter=' for i in range(0, 25*5, 25)]
        requests = []
        [requests.extend([Request(a), Request(b)]) for a, b in zip(baidu_urls, douban_urls)]
        try:
            client = Client()
            future_1 = client.submit(requests[:5])
            future_2 = client.submit(requests[5:])
            print(client)
            await asyncio.sleep(0.2)
            print(client)
            results = await future_1
            results += await future_2
            self.assertEqual(requests, [resp.request for resp in results])
        finally:
            await client.close()
