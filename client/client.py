from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import AsyncGenerator, Iterable, Optional, Tuple, Union
from weakref import WeakValueDictionary

import aiofiles
from aiohttp import ClientSession, ClientTimeout
from multidict import CIMultiDict
from yarl import URL

from .request import Request
from .response import Response


class Throttle:

    def __init__(self,
                 concurrency: int,
                 concurrency_per_host: int,
                 loop: asyncio.AbstractEventLoop) -> None:
        self._concurrency_semaphore = asyncio.Semaphore(concurrency, loop=loop)
        self._host_semaphore_factory = partial(asyncio.Semaphore, concurrency_per_host, loop=loop)
        self._hosts = WeakValueDictionary()

    @asynccontextmanager
    async def request(self, host: str) -> None:
        semaphore = self._host_semaphore_factory()
        host_semaphore = self._hosts.setdefault(host, semaphore)
        async with self._concurrency_semaphore, host_semaphore:
            yield


class Client:

    setting: dict = {
        'timeout': 20,
        'retry': 1,
        'retry_interval': 1,

        'headers': CIMultiDict({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/69.0.3497.100 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,'
                               'ja;q=0.6,zh-TW;q=0.5',
        }),
        'cookies': {},

        'concurrency': 4,
        'concurrency_per_host': 2,
        'sleep_per_request': 1,
    }

    def __init__(self, setting: Optional[dict] = None, *,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        # Update setting.
        self.setting = deepcopy(self.setting)
        if setting:
            headers = setting.pop('headers', {})
            cookies = setting.pop('cookies', {})
            self.setting['headers'].update(headers)
            self.setting['cookies'].update(cookies)
            self.setting.update(setting)
        # Initialize components.
        self._logger = logging.getLogger('client')
        self._name = self.__class__.__name__
        self._queue = asyncio.Queue()
        self._pending = 0
        self._processing = 0
        self._done = 0
        # Get event loop.
        try:
            self._loop = loop or asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self._run())

    def __repr__(self) -> str:
        batch = self._queue.qsize()
        suffix = '' if batch <= 1 else 'es'
        return (f'<{self._name} - Pending: {self._pending} ({batch} batch{suffix}) '
                f'Processing: {self._done}/{self._processing}>')

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def submit(self, requests: Union[Request, Iterable[Request]]) -> asyncio.Future:
        future = self._loop.create_future()
        single = False
        if isinstance(requests, Request):
            requests = [requests]
            single = True
        self._queue.put_nowait((future, single, requests))
        self._pending += len(requests)
        return future

    async def close(self) -> None:
        try:
            await asyncio.wait_for(self._task, 0)
        except asyncio.TimeoutError:
            await asyncio.sleep(0.5)
            self._logger.info(f'{self._name} closed')

    def _report_done(self, _) -> None:
        '''Helper function used by requests tasks.'''
        self._done += 1

    async def _run(self) -> None:
        self._logger.info(f'{self._name} start')
        timeout = ClientTimeout(total=self.setting['timeout'])
        throttle = Throttle(self.setting['concurrency'],
                            self.setting['concurrency_per_host'], self._loop)
        async with ClientSession(loop=self._loop,
                                 timeout=timeout,
                                 headers=self.setting['headers'],
                                 cookies=self.setting['cookies']) as session:
            process = partial(self._process, session=session, throttle=throttle)
            while True:
                future, single, requests = await self._queue.get()
                self._pending -= len(requests)
                self._processing = len(requests)
                self._done = 0
                if not future.cancelled():
                    coros = map(process, requests)
                    tasks = map(self._loop.create_task, coros)
                    tasks = list(tasks)
                    [task.add_done_callback(self._report_done) for task in tasks]
                    responses = await asyncio.gather(*tasks)
                    if single:
                        future.set_result(responses[0])
                    else:
                        future.set_result(responses)
                self._queue.task_done()

    async def _process(self,
                       request: Request,
                       session: ClientSession,
                       throttle: Throttle) -> Response:
        self._logger.debug(f'{request} pending')
        async with throttle.request(request.url.host):
            self._logger.debug(f'{request} processing')
            timeout, retry, retry_interval, sleep, req_params = self._make_aio_req_params(request)
            try:
                for _ in range(retry+1):
                    try:
                        async with session.request(**req_params) as aio_resp:
                            response = await self._make_response(request, aio_resp)
                            break
                    except asyncio.TimeoutError:
                        await asyncio.sleep(retry_interval)
                else:
                    raise asyncio.TimeoutError(f'{timeout}s')
            except Exception as exc:
                if not isinstance(exc, (asyncio.TimeoutError, asyncio.CancelledError)):
                    self._logger.exception('unexpected exception')
                response = await self._make_response(request, exc)
            finally:
                await asyncio.sleep(sleep)
                self._logger.debug(f'{request} complete '
                                   f'({response.status}: {response.reason})')
                return response

    async def _file_gen(self, path: Path) -> AsyncGenerator:
        async with aiofiles.open(path, 'rb') as file:
            chunk = await file.read(64*1024)
            while chunk:
                yield chunk
                chunk = await file.read(64*1024)

    def _make_aio_req_params(self, request: Request) -> Tuple:
        url = request.url
        method = request.method.name
        timeout = request.timeout or self.setting['timeout']
        retry = request.retry or self.setting['retry']
        retry_interval = request.retry_interval or self.setting['retry_interval']
        sleep = request.sleep or self.setting['sleep_per_request']
        headers = deepcopy(self.setting['headers'])
        headers.update(request.headers or {})
        params = request.params

        json = request.json
        form = request.form
        body = request.body
        text = request.text
        file = request.file and self._file_gen(request.file)
        possible_body = [json, form, body, text, file]
        assert len([v for v in possible_body if v is not None]) <= 1, 'Multiple request body.'

        return (timeout, retry, retry_interval, sleep,
                {
                    'url': url,
                    'method': method,
                    'headers': headers,
                    'timeout': timeout,
                    'params': params,
                    'json': json,
                    'data': form or body or text or file,
                })

    async def _make_response(self, request: Request,
                             result: Union[Response, Exception]) -> Response:
        if isinstance(result, Exception):
            resp = Response(
                url=URL(''),
                status=-1,
                reason=repr(result),
                content=b'',
                request=request,
            )
        else:
            resp = Response(
                url=result.url,
                status=result.status,
                reason=result.reason,
                content=await result.read(),
                request=request,
            )
        return resp
