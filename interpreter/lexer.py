from __future__ import annotations

from . import token
from .exceptions import LexerError


class Lexer:

    def __init__(self, source: str) -> None:
        self._source = iter(source)
        self._char = ''
        self._next_char = ''
        self._line_no = 1
        self._read_char()
        self._read_char()

    def _read_char(self) -> str:
        try:
            char = next(self._source)
        except StopIteration:
            char = ''
        self._char = self._next_char
        self._next_char = char

    def _is_whitespace(self) -> bool:
        return (self._char == ' '
                or self._char == '\t'
                or self._char == '\n'
                or self._char == '\r')

    def _skip_whitespace(self) -> bool:
        next_line = False
        while self._is_whitespace():
            if self._char == '\n':
                next_line = True
            self._read_char()
        return next_line

    def _read_str(self) -> bool:
        text = ''
        quote = self._char
        while (self._next_char != quote
               or self._char == '\\'):
            if not self._next_char:
                raise LexerError(f'EOF encountered while processing str {text}.')
            text += self._char
            self._read_char()
        text += self._char
        self._read_char()
        text += self._char
        self._read_char()
        return text

    def __iter__(self) -> Lexer:
        return self

    def __next__(self) -> token.Token:
        if self._skip_whitespace():
            self._line_no += 1

        if self._char == '':
            raise StopIteration

        if (self._char == '\''
                or self._char == '"'):
            return token.Word(self._read_str(), self._line_no)
        elif self._char == self._next_char == '{':
            self._read_char()
            self._read_char()
            block = ''
            while not self._char == self._next_char == '}':
                block += self._char
                self._read_char()
            self._read_char()
            self._read_char()
            return token.Block(block, self._line_no)
        else:
            word = ''
            while not self._is_whitespace() and not self._char == '':
                word += self._char
                self._read_char()
            return token.Word(word, self._line_no)
