import unittest
from pathlib import Path

from yarl import URL

from ..client.request import HTTPMethod, Request


class TestRequest(unittest.TestCase):

    def test_default_request(self):
        req = Request('url')

        self.assertEqual(req.url, URL('url'))
        self.assertEqual(req.method, HTTPMethod.GET)
        self.assertIsNone(req.headers)
        self.assertIsNone(req.timeout)
        self.assertIsNone(req.retry)
        self.assertIsNone(req.retry_interval)
        self.assertIsNone(req.sleep)
        self.assertIsNone(req.params)
        self.assertIsNone(req.json)
        self.assertIsNone(req.form)
        self.assertIsNone(req.body)
        self.assertIsNone(req.text)
        self.assertIsNone(req.file)
        self.assertIsNone(req.meta)
        self.assertEqual(repr(req), '<Request GET url>')

    def test_configured_request(self):
        req = Request(
            url='url',
            method=HTTPMethod.POST,
            headers={'headers_key': 'headers_value'},
            timeout=1,
            retry=2,
            retry_interval=3,
            sleep=4,
            params={'params_key': 'params_value'},
            json={'json_key': 'json_value'},
            form={'form_key': 'form_value'},
            body=b'body',
            text='text',
            file='./file',
            meta={'meta_key': 'meta_value'},
        )

        self.assertEqual(req.url, URL('url'))
        self.assertEqual(req.method, HTTPMethod.POST)
        self.assertEqual(req.headers, {'headers_key': 'headers_value'})
        self.assertEqual(req.timeout, 1)
        self.assertEqual(req.retry, 2)
        self.assertEqual(req.retry_interval, 3)
        self.assertEqual(req.sleep, 4)
        self.assertEqual(req.params, {'params_key': 'params_value'})
        self.assertEqual(req.json, {'json_key': 'json_value'})
        self.assertEqual(req.form, {'form_key': 'form_value'})
        self.assertEqual(req.body, b'body')
        self.assertEqual(req.text, 'text')
        self.assertEqual(req.file, Path('./file'))
        self.assertEqual(req.meta, {'meta_key': 'meta_value'})
        self.assertEqual(repr(req), '<Request POST url>')
