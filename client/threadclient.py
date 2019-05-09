from __future__ import annotations

import asyncio
import concurrent.futures as conc
import time
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Iterable, List, Optional, SupportsFloat, Union

from .client import Client
from .request import Request
from .response import Response


class ThreadFuture(conc.Future):

    def __init__(self) -> None:
        super().__init__()
        self._async_future = None

    def running(self) -> bool:
        return bool(self._async_future)

    def cancel(self) -> bool:
        while not self.running():
            time.sleep(0.1)
        return self._async_future.cancel()

    def cancelled(self) -> bool:
        if not self.running():
            return False
        return self._async_future.cancelled()

    def done(self) -> bool:
        if not self.running():
            return False
        return self._async_future.done()

    def result(self, timeout: SupportsFloat = None) -> Union[Response, List[Response]]:
        start = time.time()
        while self._async_future is None or not self._async_future.done():
            time.sleep(0.1)
            if timeout is not None and time.time() - start > timeout:
                raise conc.TimeoutError
        return self._async_future.result()


class ThreadClient:

    def __init__(self, setting: Optional[dict] = None) -> None:
        self._queue = Queue()
        self._stop = ThreadFuture()
        self._lock = Lock()
        self._thread = Thread(target=self._thread_run, args=(setting,))
        self._thread.start()
        self._repr = '<ThreadClient - Pending: 0 (0 batch) Processing: 0/0>'

    def _thread_run(self, setting) -> None:
        asyncio.run(self._async_run(setting))

    def __repr__(self) -> str:
        return self._repr

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    async def _async_run(self, setting: Optional[dict]) -> None:
        async with Client(setting) as async_client:
            while True:
                _repr = repr(async_client)
                self._repr = '<Thread' + _repr[1:]
                try:
                    # We must not use Queue.get(), which will otherwise
                    # block the whole thread.
                    future, requests = self._queue.get_nowait()
                except Empty:
                    await asyncio.sleep(0.1)
                else:
                    if future is self._stop:
                        self._queue.task_done()
                        break
                    with self._lock:
                        future._async_future = async_client.submit(requests)
                    self._queue.task_done()

    def submit(self, requests: Union[Request, Iterable[Request]]) -> conc.Future:
        future = ThreadFuture()
        self._queue.put((future, requests))
        return future

    def close(self) -> None:
        self._queue.put((self._stop, None))
        self._thread.join()
