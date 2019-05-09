import unittest

from lxml import etree
from yarl import URL

from ..client.request import Request
from ..client.response import Response


class TestResponse(unittest.TestCase):

    def test_basic_response(self):
        req = Request(
            url='url',
            meta={'meta': 'meta'},
        )
        resp = Response(
            url='url',
            status=200,
            reason='OK',
            content=b'content',
            request=req,
        )

        self.assertEqual(resp.url, URL('url'))
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.reason, 'OK')
        self.assertEqual(resp.content, b'content')
        self.assertEqual(resp.request, req)
        self.assertEqual(resp.meta, req.meta)
        self.assertEqual(repr(resp), '<Response 200 url>')

    def test_text(self):
        resp_utf8 = Response(
            url='url',
            status=200,
            reason='OK',
            content='生'.encode('utf-8'),
            request=Request('url'),
        )
        resp_jp = Response(
            url='url',
            status=200,
            reason='OK',
            content='生'.encode('shift-jis'),
            request=Request('url'),
        )

        self.assertEqual(resp_utf8.text(), '生')
        self.assertEqual(resp_jp.text('shift-jis'), '生')

        resp_utf8.text()
        resp_utf8.text('utf-8')

        cache_info = resp_utf8.text.cache_info()
        self.assertEqual(cache_info.hits, 1)
        self.assertEqual(cache_info.misses, 2)
        self.assertEqual(cache_info.maxsize, 8)
        self.assertEqual(cache_info.currsize, 2)

    def test_json(self):
        resp = Response(
            url='url',
            status=200,
            reason='OK',
            content=b'[1]',
            request=Request('url'),
        )

        self.assertEqual(resp.json(), [1])

        resp.json()
        resp.json()

        cache_info = resp.json.cache_info()
        self.assertEqual(cache_info.hits, 2)
        self.assertEqual(cache_info.misses, 1)
        self.assertEqual(cache_info.maxsize, 2)
        self.assertEqual(cache_info.currsize, 1)

    def test_etree(self):
        resp = Response(
            url='url',
            status=200,
            reason='OK',
            content=b'<a/>',
            request=Request('url'),
        )

        self.assertIsInstance(resp.etree(), etree._ElementTree)
        self.assertEqual(etree.tostring(resp.etree()), b'<html><head/><body><a/></body></html>')
        self.assertIsInstance(resp.etree(html=False), etree._ElementTree)
        self.assertEqual(etree.tostring(resp.etree(html=False)), b'<a/>')

        cache_info = resp.etree.cache_info()
        self.assertEqual(cache_info.hits, 2)
        self.assertEqual(cache_info.misses, 2)
        self.assertEqual(cache_info.maxsize, 2)
        self.assertEqual(cache_info.currsize, 2)
