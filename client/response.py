from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional, Union

import cchardet
import html5lib
from lxml import etree
from yarl import URL

from .request import Request


class Response:

    def __init__(self, *,
                 url: Union[str, URL],
                 status: int,
                 reason: str,
                 content: bytes,
                 request: Request) -> None:
        self._url = URL(url)
        self._status = status
        self._reason = reason
        self._content = content
        self._request = request
        self.text = lru_cache(maxsize=8)(self.text)
        self.json = lru_cache(maxsize=2)(self.json)
        self.etree = lru_cache(maxsize=2)(self.etree)

    def __repr__(self) -> str:
        return f'<Response {self.status} {self.url}>'

    def __eq__(self, other: Response) -> bool:
        return (self.__class__ == other.__class__
                and self._url == other._url
                and self._status == other._status
                and self._reason == other._reason
                and self._content == other._content
                and self._request == other._request)

    @property
    def url(self) -> URL:
        return self._url

    @property
    def status(self) -> int:
        return self._status

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def request(self) -> Request:
        return self._request

    @property
    def meta(self) -> dict:
        return self._request.meta

    def text(self, encoding: Optional[str] = None) -> str:
        encoding = encoding or cchardet.detect(self.content)['encoding'] or 'utf-8'
        return self.content.decode(encoding)

    def json(self) -> Any:
        return json.loads(self.content)

    def etree(self, *, html: bool = True) -> etree._ElementTree:
        if html:
            return html5lib.parse(self.content, treebuilder='lxml', namespaceHTMLElements=False)
        else:
            return etree.fromstring(self.content).getroottree()
