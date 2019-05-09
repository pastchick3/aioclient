class InterpreterError(Exception):
    pass


class LexerError(InterpreterError):
    pass


class ParserError(InterpreterError):
    pass


class EvaluatorError(InterpreterError):
    pass
