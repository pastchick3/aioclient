from dataclasses import dataclass, field
from typing import List, TypeVar, Union

    
T = TypeVar('T')


#-----------------------------------------------------------------------
# Nodes
#-----------------------------------------------------------------------


@dataclass
class Node:
    pass


@dataclass
class IdentifierNode(Node):

    text: str


@dataclass
class PyObjectNode(Node):

    text: str


@dataclass
class PyBlockNode(Node):
    
    text: str


@dataclass
class TextNode(Node):
    
    text: str


@dataclass
class EmptyNode(Node):
    pass


@dataclass
class PlaceholderNode(Node):
    pass


OptionalNode = Union[EmptyNode, T]
VariableNode = Union[IdentifierNode, T]
OptVarNode = Union[EmptyNode, IdentifierNode, T]
ImplicitNode = Union[PlaceholderNode, T]


@dataclass
class TimeIntervalNode(Node):

    num: VariableNode[PyObjectNode]
    multiple: PyObjectNode


@dataclass
class SetNode(Node):

    key: TextNode
    value: PyObjectNode
    field: TextNode


@dataclass
class BranchNode(Node):

    attr: OptionalNode[TextNode]
    test_op: OptionalNode[TextNode]
    test_obj: OptionalNode[PyObjectNode]
    content_type: TextNode
    action: PyBlockNode


#-----------------------------------------------------------------------
# Expressions
#-----------------------------------------------------------------------


@dataclass
class Expression:
    pass


@dataclass
class IdentifierExpression(Expression):

    ident: IdentifierNode


@dataclass
class PlaceholderExpression(Expression):
    pass


VariableExpression = Union[IdentifierExpression, T]
ImplicitExpression = Union[PlaceholderExpression, T]


@dataclass
class RequestExpression(Expression):

    method: TextNode
    url: ImplicitNode[PyObjectNode]
    timeout: OptionalNode[TimeIntervalNode]
    retry: OptVarNode[PyObjectNode]
    retry_interval: OptVarNode[PyObjectNode]
    sleep: OptVarNode[PyObjectNode]
    set_list: List[SetNode]


@dataclass
class FutureExpression(Expression):

    expr: ImplicitExpression[VariableExpression[RequestExpression]]


@dataclass
class ResponseExpression(Expression):

    expr: ImplicitExpression[VariableExpression[FutureExpression]]


@dataclass
class ResultExpression(Expression):

    resp: ImplicitExpression[VariableExpression[ResponseExpression]]
    branches: List[BranchNode]


@dataclass
class ThenExpression(Expression):

    expr: Union[
        RequestExpression,
        FutureExpression,
        ResponseExpression,
        ResultExpression,
    ]


#-----------------------------------------------------------------------
# Statements
#-----------------------------------------------------------------------


@dataclass
class Statement:
    pass


@dataclass
class Program:

    statements: List[Statement] = field(default_factory=list)


@dataclass
class LetStatement(Statement):

    ident: TextNode
    expr: Expression


@dataclass
class ExpressionStatement(Statement):

    expr: Expression
