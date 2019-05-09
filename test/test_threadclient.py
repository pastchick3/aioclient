import concurrent.futures as conc
import logging
import unittest

from yarl import URL

from ..client.request import HTTPMethod, Request
from ..client.threadclient import ThreadClient


class TestThreadClient(unittest.TestCase):

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

    def test_thread_future_cancel(self):
        client = ThreadClient()
        req = Request('http://www.baidu.com/')
        try:
            fut = client.submit(req)
            self.assertEqual(fut.cancelled(), False)
            self.assertEqual(fut.done(), False)
            fut.cancel()
            self.assertEqual(fut.done(), True)
        finally:
            client.close()

    def test_thread_future_timeout(self):
        client = ThreadClient()
        req = Request('https://www.google.com/')
        try:
            fut = client.submit(req)
            with self.assertRaises(conc.TimeoutError):
                fut.result(0.5)
            fut.cancel()
        finally:
            client.close()

    def test_basic(self):
        setting = {
            'headers': {'global-headers': 'global_headers_value'},
            'cookies': {'global_cookies': 'global_cookies_value'},
        }
        client = ThreadClient(setting)
        self.assertEqual(repr(client), '<ThreadClient - Pending: 0 (0 batch) Processing: 0/0>')
        req = Request(
            url='http://www.httpbin.org/post',
            method=HTTPMethod.POST,
            headers={'headers': 'headers_value'},
            params={'params': 'params_value'},
            meta={'k': 'v'},
        )
        try:
            resp = client.submit(req).result()
            assert resp.status == 200
            self.assertEqual(resp.url, URL('http://www.httpbin.org/post?params=params_value'))
            self.assertEqual(resp.json()['headers']['Global-Headers'], 'global_headers_value')
            self.assertEqual(resp.json()['headers']['Headers'], 'headers_value')
            self.assertEqual(resp.json()['headers']['Cookie'], 'global_cookies=global_cookies_value')
            self.assertEqual(resp.meta, {'k': 'v'})
        finally:
            client.close()

    def test_context_manager(self):
        setting = {
            'headers': {'global-headers': 'global_headers_value'},
            'cookies': {'global_cookies': 'global_cookies_value'},
        }
        with ThreadClient(setting) as client:
            self.assertEqual(repr(client), '<ThreadClient - Pending: 0 (0 batch) Processing: 0/0>')
            req = Request(
                url='http://www.httpbin.org/post',
                method=HTTPMethod.POST,
                headers={'headers': 'headers_value'},
                params={'params': 'params_value'},
                meta={'k': 'v'},
            )
            resp = client.submit(req).result()
            assert resp.status == 200
            self.assertEqual(resp.url, URL('http://www.httpbin.org/post?params=params_value'))
            self.assertEqual(resp.json()['headers']['Global-Headers'], 'global_headers_value')
            self.assertEqual(resp.json()['headers']['Headers'], 'headers_value')
            self.assertEqual(resp.json()['headers']['Cookie'], 'global_cookies=global_cookies_value')
            self.assertEqual(resp.meta, {'k': 'v'})
