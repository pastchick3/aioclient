from __future__ import annotations

from itertools import takewhile
from typing import Any, List

from pampy import match
from yarl import URL

from ..client.client import Client
from ..client.request import HTTPMethod, Request
from ..client.response import Response
from ..interpreter import ast
from ..interpreter.exceptions import EvaluatorError


class Evaluator:

    def __init__(self, client: Client) -> None:
        self._client = client

    async def eval(self, program: ast.Program, *,
                   global_env: dict = None,
                   local_env: dict = None) -> Any:
        self._global_env = global_env or {}
        self._local_env = local_env or {}
        self._env = {}
        self._result = None
        for stmt in program.statements:
            self._result = await self._eval_stmt(stmt)
        return self._result

    #-------------------------------------------------------------------
    # Evaluate Statements
    #-------------------------------------------------------------------

    async def _eval_stmt(self, stmt: ast.Statement) -> Any:
        if isinstance(stmt, ast.LetStatement):
            return await self._eval_let_stmt(stmt)
        else:
            return await self._eval_expr_stmt(stmt)

    async def _eval_let_stmt(self, stmt: ast.LetStatement) -> Any:
        ident = self._eval_text_node(stmt.ident)
        self._env[ident] = await self._eval_expr(stmt.expr)

    async def _eval_expr_stmt(self, stmt: ast.ExpressionStatement) -> Any:
        return await self._eval_expr(stmt.expr)

    #-------------------------------------------------------------------
    # Evaluate Expressions
    #-------------------------------------------------------------------

    async def _eval_expr(self, expr: ast.Expression) -> Any:
        if isinstance(expr, ast.IdentifierExpression):
            return await self._eval_identifier_expr(expr)
        elif isinstance(expr, ast.PlaceholderExpression):
            return await self._eval_placeholder_expr(expr)
        elif isinstance(expr, ast.RequestExpression):
            return await self._eval_request_expr(expr)
        elif isinstance(expr, ast.ResponseExpression):
            return await self._eval_response_expr(expr)
        elif isinstance(expr, ast.FutureExpression):
            return await self._eval_future_expr(expr)
        elif isinstance(expr, ast.ResultExpression):
            return await self._eval_result_expr(expr)
        elif isinstance(expr, ast.ThenExpression):
            return await self._eval_then_expr(expr)

    async def _eval_identifier_expr(self, expr: ast.IdentifierExpression) -> Any:
        return self._eval_identifier_node(expr.ident)

    async def _eval_placeholder_expr(self, expr: ast.PlaceholderExpression) -> Any:
        return self._result

    async def _eval_request_expr(self, expr: ast.RequestExpression) -> Any:
        req_params = {}
        req_params['method'] = match(self._eval_text_node(expr.method),
            'get', HTTPMethod.GET,
            'post', HTTPMethod.POST,
        )
        local = locals()
        for name in ['timeout', 'retry', 'retry_interval', 'sleep']:
            exec(
                f'{name} = match(expr.{name},\n'
                f'    ast.EmptyNode, lambda _: None,\n'
                f'    ast.TimeIntervalNode, self._eval_time_interval_node,\n'
                f'    ast.IdentifierNode, self._eval_identifier_node,\n'
                f'    ast.PyObjectNode, self._eval_py_object_node,\n'
                f')\n',
                globals(),
                local,
            )
        req_params['timeout'] = local['timeout']
        req_params['retry'] = local['retry']
        req_params['retry_interval'] = local['retry_interval']
        req_params['sleep'] = local['sleep']
        for key, value, field in self._eval_set_list(expr.set_list):
            if field == 'body':
                req_params[key] = value
            elif field == 'query':
                req_params.setdefault('params', {})[key] = value
            else:
                req_params.setdefault(field, {})[key] = value
        urls = match(expr.url,
            ast.PlaceholderNode, self._eval_placeholder_node,
            ast.PyObjectNode, self._eval_py_object_node,
        )
        if isinstance(urls, (str, URL)):
            return Request(urls, **req_params)
        else:
            return [Request(url, **req_params) for url in urls]

    async def _eval_future_expr(self, expr: ast.FutureExpression) -> Any:
        requests = await self._eval_expr(expr.expr)
        return self._client.submit(requests)

    async def _eval_response_expr(self, expr: ast.ResponseExpression) -> Any:
        future = await self._eval_expr(expr.expr)
        return await future

    async def _eval_result_expr(self, expr: ast.ResultExpression) -> Any:
        responses = await self._eval_expr(expr.resp)
        single = False
        if isinstance(responses, Response):
            single = True
            responses = [responses]
        results = []
        for response in responses:
            for branch in expr.branches:
                flag, result = self._eval_branch_node(branch, response)
                if flag:
                    results.append(result)
                    break
            else:
                results.append(response)
        if single:
            return results[0]
        else:
            return results

    async def _eval_then_expr(self, expr: ast.ThenExpression) -> Any:
        return await self._eval_expr(expr.expr)

    #-------------------------------------------------------------------
    # Evaluate Nodes
    #-------------------------------------------------------------------

    def _eval_identifier_node(self, node: ast.IdentifierNode) -> Any:
        try:
            return self._env[node.text]
        except KeyError:
            try:
                return self._local_env[node.text]
            except KeyError:
                return self._global_env[node.text]

    def _eval_py_object_node(self, node: ast.PyObjectNode) -> Any:
        try:
            return eval(node.text)
        except NameError:
            return self._eval_identifier_node(node)

    def _eval_py_block_node(self, node: ast.PyBlockNode, response: Response, obj: Any) -> Any:
        text = node.text
        rows = text.split('\n')
        rows[0] = 'def f(response, obj):'
        space_len = len(list(takewhile(lambda ch: ch == ' ', rows[1]))) - 4
        for i in range(len(rows)-1):
            rows[i+1] = rows[i+1][space_len:]
        rows.append('result = f(response, obj)')
        text = '\n'.join(rows)
        env = {
            'response': response,
            'obj': obj,
        }
        exec(text, env)
        return env['result']

    def _eval_text_node(self, node: ast.TextNode) -> Any:
        return node.text

    def _eval_placeholder_node(self, node: ast.PlaceholderNode) -> Any:
        return self._result

    def _eval_time_interval_node(self, node: ast.TimeIntervalNode) -> Any:
        num = match(node.num,
            ast.IdentifierNode, self._eval_identifier_node,
            ast.PyObjectNode, self._eval_py_object_node,
        )
        multiple = self._eval_py_object_node(node.multiple)
        return num * multiple

    def _eval_set_list(self, set_list: List[ast.SetNode]) -> Any:
        return [(self._eval_text_node(node.key),
                 self._eval_py_object_node(node.value),
                 self._eval_text_node(node.field)) for node in set_list]

    def _eval_branch_node(self, node: ast.BranchNode, response: Response) -> Any:
        if isinstance(node.attr, ast.EmptyNode):
            flag = True
        else:
            raw_attr = self._eval_text_node(node.attr)
            attr = eval(f'response.{raw_attr}')
            attr = str(attr) if raw_attr == 'url' else attr
            test_op = self._eval_text_node(node.test_op)
            test_obj = self._eval_py_object_node(node.test_obj)
            flag = eval(f'test_obj {test_op} attr')
        if flag:
            raw_type = self._eval_text_node(node.content_type)
            content_type = match(raw_type,
                'bytes', 'content',
                'str', 'text()',
                'json', 'json()',
                'html', 'etree()',
                'xml', 'etree(html=False)',
                strict=False,
            )
            if content_type is False:
                raise EvaluatorError(f'Unknown content type: {raw_type}')
            try:
                obj = eval(f'response.{content_type}')
                if isinstance(node.action, ast.PyBlockNode):
                    result = self._eval_py_block_node(node.action, response, obj)
                else:
                    result = self._eval_py_object_node(node.action)(response, obj)
            except Exception as exc:
                result = exc
        else:
            result = None
        return flag, result
