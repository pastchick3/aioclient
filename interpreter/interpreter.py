from __future__ import annotations

from typing import Any, Optional

from ..client.client import Client
from .evaluator import Evaluator
from .lexer import Lexer
from .parser import Parser


class Interpreter:

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client or Client()

    async def run(self, source: str,
                  global_env: dict = None,
                  local_env: dict = None) -> Any:
        lexer = Lexer(source)
        parser = Parser(lexer)
        program = parser.parse()
        evaluator = Evaluator(self._client)
        return await evaluator.eval(program,
                                    global_env=global_env,
                                    local_env=local_env)

    async def close(self) -> None:
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
