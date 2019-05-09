from __future__ import annotations

import re


#-----------------------------------------------------------------------
# Root Token Class
#-----------------------------------------------------------------------


class Token:

    def __new__(cls, text: str, line_no: int) -> Token:
        return super().__new__(cls)

    def __init__(self, text: str, line_no: int) -> None:
        self.text = text
        self.line_no = line_no

    def __eq__(self, other: Token) -> bool:
        return (self.__class__ == other.__class__
                and self.text == other.text)

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}({self.text}) at line {self.line_no}>'


#-----------------------------------------------------------------------
# 1st Layer Subclasses
#-----------------------------------------------------------------------


class Block(Token):
    pass


class Word(Token):

    kw_obj: re.Pattern = re.compile(
        r'let|=|get|post|with|'
        r'timeout|retry|sleep|set|'
        r'send|wait|process|whose|as|'
        r'then|otherwise'
    )

    def __new__(cls, text: str, line_no: int) -> Word:
        if cls.kw_obj.fullmatch(text):
            return Keyword.__new__(Keyword, text, line_no)
        else:
            return super().__new__(cls, text, line_no)


#-----------------------------------------------------------------------
# 2nd Layer Subclasses
#-----------------------------------------------------------------------


class Keyword(Word):

    def __new__(cls, text: str, line_no: int) -> Keyword:
        cls_name = 'Eq' if text == '=' else text.capitalize()
        return eval(f'Token.__new__({cls_name}, text, line_no)')


class Let(Keyword): pass
class Eq(Keyword): pass
class Get(Keyword): pass
class Post(Keyword): pass
class With(Keyword): pass
class Timeout(Keyword): pass
class Retry(Keyword): pass
class Sleep(Keyword): pass
class Set(Keyword): pass
class Send(Keyword): pass
class Wait(Keyword): pass
class Process(Keyword): pass
class Whose(Keyword): pass
class As(Keyword): pass
class Then(Keyword): pass
class Otherwise(Keyword): pass
