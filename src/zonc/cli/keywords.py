"""Zonetic keyword table.

Maps source-code identifiers to their TokenType.
Imported by the Lexer and by the REPL completer.
"""

from zonc.scanner import TokenType

KEYWORDS = {
    "int64":    TokenType.KEYWORD_INT64,
    "int32":    TokenType.KEYWORD_INT32,
    "float":    TokenType.KEYWORD_FLOAT,
    "double":   TokenType.KEYWORD_DOUBLE,
    "string":   TokenType.KEYWORD_STRING,
    "bool":     TokenType.KEYWORD_BOOL,
    "mut":      TokenType.KEYWORD_MUT,
    "inmut":    TokenType.KEYWORD_INMUT,
    "if":       TokenType.KEYWORD_IF,
    "elif":     TokenType.KEYWORD_ELIF,
    "else":     TokenType.KEYWORD_ELSE,
    "while":    TokenType.KEYWORD_WHILE,
    "infinity": TokenType.KEYWORD_INFINITY,
    "continue": TokenType.KEYWORD_CONTINUE,
    "break":    TokenType.KEYWORD_BREAK,
    "and":      TokenType.GATE_AND,
    "or":       TokenType.GATE_OR,
    "not":      TokenType.GATE_NOT,
    "true":     TokenType.LITERAL_TRUE,
    "false":    TokenType.LITERAL_FALSE,
    "give":     TokenType.KEYWORD_GIVE,
    "func":     TokenType.KEYWORD_FUNC,
    "void":     TokenType.KEYWORD_VOID,
    "return":   TokenType.KEYWORD_RETURN,
    "struct":   TokenType.KEYWORD_STRUCT,
    "band":     TokenType.BIT_AND,
    "bxor":     TokenType.BIT_XOR,
    "bor":      TokenType.BIT_OR,
    "bnot":     TokenType.BIT_NOT,
}