import re
from functools import partial

from pampy import _, match

from . import ast, token
from .exceptions import ParserError


class Parser:

    def __init__(self, lexer):
        self._lexer = lexer
        self._token = ''
        self._read_token()

    def _read_token(self):
        try:
            self._token = next(self._lexer)
        except StopIteration:
            self._token = ''
        return self._token

    def parse(self):
        program = ast.Program()
        while self._token:
            program.statements.append(self._parse_stmt())
        return program

    def _require(self, token, expected):
        if not token:
            raise ParserError(f'Expected: {expected}, got: EOF')
        if not re.search(expected, token.text):
            raise ParserError(f'Expected: {expected}, got: {token.text}, at line {token.line_no}')

    #-------------------------------------------------------------------
    # Parse Statements
    #-------------------------------------------------------------------

    def _parse_stmt(self):
        return match(self._token,
            token.Let, self._parse_let_stmt,
            _, self._parse_expr_stmt,
        )
    
    def _parse_let_stmt(self, _):
        self._read_token()
        ident = ast.TextNode(self._token.text)
        self._require(self._read_token(), '=')
        self._read_token()
        return ast.LetStatement(ident, self._parse_expr())

    def _parse_expr_stmt(self, _):
        return ast.ExpressionStatement(self._parse_expr())

    #-------------------------------------------------------------------
    # Parse Expressions
    #-------------------------------------------------------------------

    def _parse_expr(self, *, implicit=False):
        return match(self._token,
            token.Get, partial(self._parse_request_expr, implicit=implicit),
            token.Post, partial(self._parse_request_expr, implicit=implicit),
            token.Send, partial(self._parse_future_expr, implicit=implicit),
            token.Wait, partial(self._parse_response_expr, implicit=implicit),
            token.Process, partial(self._parse_result_expr, implicit=implicit),
            token.Then, self._parse_then_expr,
            _, self._parse_identifier_expr,
        )

    def _parse_identifier_expr(self, _):
        ident = ast.IdentifierNode(self._token.text)
        self._read_token()
        return ast.IdentifierExpression(ident)
    
    def _parse_then_expr(self, _):
        self._read_token()
        expr = self._parse_expr(implicit=True)
        return ast.ThenExpression(expr)

    def _parse_request_expr(self, _, *, implicit=False):
        method = ast.TextNode(self._token.text)
        url = ast.EmptyNode()
        timeout = ast.EmptyNode()
        retry = ast.EmptyNode()
        retry_interval = ast.EmptyNode()
        sleep = ast.EmptyNode()
        set_list = []

        if method.text == 'get':
            self._require(self._read_token(), 'from')
        elif method.text == 'post':
            self._require(self._read_token(), 'to')
        self._read_token()
        if implicit:
            url = ast.PlaceholderNode()
        else:
            cache = self._cache_until_next_keyword()
            if not cache:
                if not self._token:
                    raise ParserError(f'url required, got EOF')
                raise ParserError(f'url required, at line {self._token.line_no}')
            url = ast.PyObjectNode(' '.join(tok.text for tok in cache))

        if isinstance(self._token, token.With):
            self._read_token()
            last_kw = self._token
            self._read_token()
            cache = self._cache_until_next_keyword()
            kw = self._token
            while True:
                if isinstance(last_kw, token.Timeout):
                    timeout = self._parse_timeout(cache)
                elif isinstance(last_kw, token.Retry):
                    retry, retry_interval = self._parse_retry(cache)
                elif isinstance(last_kw, token.Sleep):
                    sleep = self._parse_sleep(cache)
                elif isinstance(last_kw, token.Set):
                    set_list.append(self._parse_set(cache))
                if isinstance(kw, (token.Timeout, token.Retry, token.Sleep, token.Set)):
                    last_kw = kw
                    self._read_token()
                    cache = self._cache_until_next_keyword()
                    kw = self._token
                else:
                    break

        return ast.RequestExpression(
            method=method,
            url=url,
            timeout=timeout,
            retry=retry,
            retry_interval=retry_interval,
            sleep=sleep,
            set_list=set_list,
        )

    def _parse_future_expr(self, _, *, implicit=False):
        self._read_token()
        if implicit:
            expr = ast.PlaceholderExpression()
        else:
            expr = self._parse_expr()
        return ast.FutureExpression(expr)

    def _parse_response_expr(self, _, *, implicit=False):
        self._read_token()
        if implicit:
            expr = ast.PlaceholderExpression()
        else:
            expr = self._parse_expr()
        return ast.ResponseExpression(expr)

    def _parse_result_expr(self, _, *, implicit=False):
        self._read_token()
        if implicit:
            resp = ast.PlaceholderExpression()
        else:
            resp = self._parse_expr()
        branches = []
        while isinstance(self._token, (token.Whose, token.Otherwise, token.As)):
            branches.append(self._parse_branch())
        return ast.ResultExpression(resp, branches)

    #-------------------------------------------------------------------
    # Helper Methods
    #-------------------------------------------------------------------

    def _parse_time_interval(self, cache):
        num = ast.PyObjectNode(cache[0].text)
        self._require(cache[1], 'second|minute')
        multiple = match(cache[1].text,
            'second', ast.PyObjectNode('1'),
            'seconds', ast.PyObjectNode('1'),
            'minute', ast.PyObjectNode('60'),
            'minutes', ast.PyObjectNode('60'),
            strict=False,
        )
        return ast.TimeIntervalNode(num, multiple)

    def _parse_timeout(self, cache):
        return self._parse_time_interval(cache)

    def _parse_retry(self, cache):
        retry = ast.PyObjectNode('None')
        retry_interval = ast.PyObjectNode('None')
        while cache:
            if cache[0].text == 'at':
                retry_interval = self._parse_time_interval(cache[1:3])
                self._require(cache[3], 'apart')
                cache = cache[4:]
            else:
                retry = ast.PyObjectNode(cache[0].text)
                self._require(cache[1], 'time')
                cache = cache[2:]
        return retry, retry_interval

    def _parse_sleep(self, cache):
        self._require(cache[2], 'per')
        self._require(cache[3], 'request')
        return self._parse_time_interval(cache[:2])

    def _parse_set(self, cache):
        key = ast.TextNode(cache[0].text)
        self._require(cache[1], 'equals')
        text = [tok.text for tok in cache[2:-2]]
        value = ast.PyObjectNode(' '.join(text))
        self._require(cache[-2], 'in')
        field = ast.TextNode(cache[-1].text)
        return ast.SetNode(key, value, field)

    def _parse_branch(self):
        if isinstance(self._token, token.Otherwise):
            self._read_token()

        if isinstance(self._token, token.As):
            attr = ast.EmptyNode()
            test_op = ast.EmptyNode()
            test_obj = ast.EmptyNode()
            self._read_token()
            content_type = ast.TextNode(self._token.text)
            self._require(self._read_token(), 'with')
            self._read_token()
            if isinstance(self._token, token.Word):
                action = ast.IdentifierNode(self._token.text)
            elif isinstance(self._token, token.Block):
                action = ast.PyBlockNode(self._token.text)
            self._read_token()

        elif isinstance(self._token, token.Whose):
            # attr
            self._read_token()
            attr = ast.TextNode(self._token.text)
            self._read_token()
            # test_op
            test_op = ''
            while True:
                test_op = match(test_op,
                    ' equals', ast.TextNode('=='),
                    ' does not equal', ast.TextNode('!='),
                    ' contains', ast.TextNode('in'),
                    ' does not contain', ast.TextNode('not in'),
                    _, lambda test_op: test_op + ' ' + self._token.text
                )
                if isinstance(test_op, ast.TextNode):
                    break
                else:
                    self._read_token()
            # test_obj
            cache = []
            while not isinstance(self._token, token.As):
                cache.append(self._token)
                self._read_token()
            test_obj = ast.PyObjectNode(' '.join(tok.text for tok in cache))
            # content_type
            self._read_token()
            content_type = ast.TextNode(self._token.text)
            self._require(self._read_token(), 'with')
            # action
            self._read_token()
            if isinstance(self._token, token.Word):
                action = ast.IdentifierNode(self._token.text)
            elif isinstance(self._token, token.Block):
                action = ast.PyBlockNode(self._token.text)
            self._read_token()
        
        return ast.BranchNode(
            attr=attr,
            test_op=test_op,
            test_obj=test_obj,
            content_type=content_type,
            action=action,
        )

    def _cache_until_next_keyword(self):
        cache = []
        while self._token and not isinstance(self._token, token.Keyword):
            cache.append(self._token)
            self._read_token()
        return cache
