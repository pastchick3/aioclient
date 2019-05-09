from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import Optional, SupportsFloat, Union

from yarl import URL


class HTTPMethod(Enum):

    GET = auto()
    POST = auto()


class Request:

    def __init__(self, url: Union[str, URL], *,
                 method: HTTPMethod = HTTPMethod.GET,
                 timeout: Optional[SupportsFloat] = None,
                 retry: Optional[int] = None,
                 retry_interval: Optional[SupportsFloat] = None,
                 sleep: Optional[SupportsFloat] = None,
                 headers: Optional[dict] = None,
                 params: Optional[dict] = None,
                 json: Optional[dict] = None,
                 form: Optional[dict] = None,
                 body: Optional[bytes] = None,
                 text: Optional[str] = None,
                 file: Optional[Union[str, Path]] = None,
                 meta: Optional[dict] = None) -> None:
        self.url = URL(url)
        self.method = method
        self.headers = headers
        self.timeout = timeout
        self.retry = retry
        self.retry_interval = retry_interval
        self.sleep = sleep
        self.params = params
        self.json = json
        self.form = form
        self.body = body
        self.text = text
        self.file = Path(file) if file is not None else file
        self.meta = meta

    def __repr__(self) -> str:
        return f'<Request {self.method.name} {self.url}>'

    def __eq__(self, other: Request) -> bool:
        return (
            self.__class__ == other.__class__
            and self.url == other.url
            and self.method == other.method
            and self.headers == other.headers
            and self.timeout == other.timeout
            and self.retry == other.retry
            and self.retry_interval == other.retry_interval
            and self.sleep == other.sleep
            and self.params == other.params
            and self.json == other.json
            and self.form == other.form
            and self.body == other.body
            and self.text == other.text
            and self.file == other.file
            and self.meta == other.meta
        )
