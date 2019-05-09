import unittest

from ..interpreter.ast import *
from ..interpreter.exceptions import ParserError
from ..interpreter.lexer import Lexer
from ..interpreter.parser import Parser


class TestParser(unittest.TestCase):

    def test_parser(self):
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

        expected_program = Program()
        expected_program.statements.append(
            LetStatement(
                TextNode('request'),
                RequestExpression(
                    method=TextNode('get'),
                    url=PyObjectNode("'http://www.baidu.com/s'"),
                    timeout=TimeIntervalNode(
                        num=PyObjectNode('5'),
                        multiple=PyObjectNode('60'),
                    ),
                    retry=PyObjectNode('3'),
                    retry_interval=TimeIntervalNode(
                        num=PyObjectNode('10'),
                        multiple=PyObjectNode('1'),
                    ),
                    sleep=TimeIntervalNode(
                        num=PyObjectNode('1'),
                        multiple=PyObjectNode('1'),
                    ),
                    set_list=[
                        SetNode(
                            TextNode('wd'),
                            PyObjectNode("'BNF'"),
                            TextNode('query'),
                        ),
                    ]
                )
            )
        )
        expected_program.statements.append(
            LetStatement(
                TextNode('future'),
                FutureExpression(
                    IdentifierExpression(
                        IdentifierNode('request')
                    )
                )
            )
        )
        expected_program.statements.append(
            LetStatement(
                TextNode('response'),
                ResponseExpression(
                    IdentifierExpression(
                        IdentifierNode('future')
                    )
                )
            )
        )
        expected_program.statements.append(
            ExpressionStatement(
                ResultExpression(
                    resp=IdentifierExpression(
                        IdentifierNode('response')
                    ),
                    branches=[
                        BranchNode(
                            attr=TextNode('status'),
                            test_op=TextNode('=='),
                            test_obj=PyObjectNode('200'),
                            content_type=TextNode('html'),
                            action=PyBlockNode('''
                    print(obj.xpath('//title')[0].text)
                ''')
                        ),
                        BranchNode(
                            attr=EmptyNode(),
                            test_op=EmptyNode(),
                            test_obj=EmptyNode(),
                            content_type=TextNode('bytes'),
                            action=PyBlockNode('''
                    return None
                ''')
                        ),
                    ]
                )
            )
        )
        expected_program.statements.append(
            ExpressionStatement(
                RequestExpression(
                    method=TextNode('post'),
                    url=PyObjectNode("'another str'"),
                    timeout=EmptyNode(),
                    retry=EmptyNode(),
                    retry_interval=EmptyNode(),
                    sleep=EmptyNode(),
                    set_list=[]
                )
            )
        )
        expected_program.statements.append(
            ExpressionStatement(
                ThenExpression(
                    ResultExpression(
                        resp=PlaceholderExpression(),
                        branches=[
                            BranchNode(
                                attr=EmptyNode(),
                                test_op=EmptyNode(),
                                test_obj=EmptyNode(),
                                content_type=TextNode('bytes'),
                                action=PyBlockNode('''
                return None
            ''')
                            ),
                        ]
                    )
                )
            )
        )

        lexer = Lexer(source)
        parser = Parser(lexer)
        program = parser.parse()
        self.assertEqual(program, expected_program)

    def test_error(self):
        source = 'let a b'
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: =, got: b, at line 1'):
            parser.parse()

        source = 'get to'
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: from, got: to, at line 1'):
            parser.parse()

        source = 'post from'
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: to, got: from, at line 1'):
            parser.parse()

        source = 'post to'
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'url required'):
            parser.parse()

        source = '''get from url with
                        timeout 5 hours'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: second|minute, got: hours, at line 2'):
            parser.parse()

        source = '''get from url with
                        retry 5 hours'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: time, got: hours, at line 2'):
            parser.parse()

        source = '''get from url with
                        retry at 10 seconds every'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: apart, got: every, at line 2'):
            parser.parse()

        source = '''get from url with
                        sleep 1 second every request'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: per, got: every, at line 2'):
            parser.parse()

        source = '''get from url with
                        sleep 1 second per req'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: request, got: req, at line 2'):
            parser.parse()

        source = '''get from url with
                        set wd equal 'BNF' in query'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: equals, got: equal, at line 2'):
            parser.parse()

        source = '''get from url with
                        set wd equals 'BNF' side query'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: in, got: side, at line 2'):
            parser.parse()

        source = '''process response as etree using func'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: with, got: using, at line 1'):
            parser.parse()

        source = '''process response whose status equals 200 as etree using func'''
        lexer = Lexer(source)
        parser = Parser(lexer)
        with self.assertRaisesRegex(ParserError, 'Expected: with, got: using, at line 1'):
            parser.parse()
