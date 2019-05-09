import unittest

from ..interpreter.exceptions import LexerError
from ..interpreter.lexer import Lexer
from ..interpreter.token import *


class TestLexer(unittest.TestCase):

    def test_lexer(self):
        source = '''
            let request = get from 'http://www.baidu.com/s' with
                            timeout 5 minutes
                            retry 3 times at 10 seconds apart
                            sleep 1 second per request
                            set wd equals 'BNF' in query

            let future = send request
            
            let response = wait future

            process response
                whose status equals 200 as html with {{
                    print(obj.xpath('//title')[0].text)
                }}
                otherwise as bytes with {{
                    return None
                }}

            post to 'another str'
            then process as bytes with {{
                return None
            }}
        '''

        expected_tokens = [
            Let('let', 1),
            Word('request', 1),
            Eq('=', 1),
            Get('get', 1),
            Word('from', 1),
            Word("'http://www.baidu.com/s'", 1),
            With('with', 1),
            Timeout('timeout', 2),
            Word('5', 2),
            Word('minutes', 2),
            Retry('retry', 3),
            Word('3', 3),
            Word('times', 3),
            Word('at', 3),
            Word('10', 3),
            Word('seconds', 3),
            Word('apart', 3),
            Sleep('sleep', 4),
            Word('1', 4),
            Word('second', 4),
            Word('per', 4),
            Word('request', 4),
            Set('set', 5),
            Word('wd', 5),
            Word('equals', 5),
            Word("'BNF'", 5),
            Word('in', 5),
            Word('query', 5),

            Let('let', 7),
            Word('future', 7),
            Eq('=', 7),
            Send('send', 7),
            Word('request', 7),

            Let('let', 9),
            Word('response', 9),
            Eq('=', 9),
            Wait('wait', 9),
            Word('future', 9),

            Process('process', 11),
            Word('response', 11),
            Whose('whose', 12),
            Word('status', 12),
            Word('equals', 12),
            Word('200', 12),
            As('as', 12),
            Word('html', 12),
            With('with', 12),
            Block('''
                    print(obj.xpath('//title')[0].text)
                ''', 12),
            Otherwise('otherwise', 13),
            As('as', 13),
            Word('bytes', 13),
            With('with', 13),
            Block('''
                    return None
                ''', 13),

            Post('post', 15),
            Word('to', 15),
            Word("'another str'", 15),
            Then('then', 16),
            Process('process', 16),
            As('as', 16),
            Word('bytes', 16),
            With('with', 16),
            Block('''
                return None
            ''', 16),
        ]

        lexer = Lexer(source)
        tokens = list(lexer)
        self.assertEqual(tokens, expected_tokens, tokens)

    def test_error(self):
        source = '''
            "123
        '''
        lexer = Lexer(source)
        with self.assertRaisesRegex(LexerError, 'EOF'):
            list(lexer)
