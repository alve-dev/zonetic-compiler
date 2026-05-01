from enum import Enum, auto

class TokenType(Enum):
    # KEYWORDS
    KEYWORD_INT64 = auto()
    KEYWORD_INT32 = auto()
    KEYWORD_FLOAT = auto()
    KEYWORD_DOUBLE = auto()
    KEYWORD_BOOL = auto()
    KEYWORD_STRING = auto()
    KEYWORD_VOID = auto()

    KEYWORD_MUT = auto()
    KEYWORD_INMUT = auto()
    
    KEYWORD_IF = auto()
    KEYWORD_ELSE = auto()
    KEYWORD_ELIF = auto()
    
    KEYWORD_WHILE = auto()
    KEYWORD_INFINITY = auto()
    KEYWORD_BREAK = auto()
    KEYWORD_CONTINUE = auto()
    
    KEYWORD_GIVE = auto()
    
    KEYWORD_FUNC = auto()
    KEYWORD_RETURN = auto()
    
    KEYWORD_STRUCT = auto()
    
    # LOGIC GATES BOOL
    GATE_AND = auto()
    GATE_OR = auto()
    GATE_NOT = auto()
    
    
    # Operators
    OPERATOR_PLUS = auto()
    OPERATOR_MINUS = auto()
    OPERATOR_MULT = auto()
    OPERATOR_POW = auto()
    OPERATOR_MOD = auto()
    OPERATOR_DIV = auto()
    
    OPERATOR_ASSIGN = auto()
    OPERATOR_MINUS_ASSIGN = auto()
    OPERATOR_PLUS_ASSIGN = auto()
    OPERATOR_MULT_ASSIGN = auto()
    OPERATOR_POW_ASSIGN = auto()
    OPERATOR_MOD_ASSIGN = auto()
    OPERATOR_DIV_ASSIGN = auto()
    
    OPERATOR_EQUAL = auto()
    OPERATOR_NOT_EQUAL = auto()
    OPERATOR_GREATER = auto()
    OPERATOR_GREATER_EQUAL = auto()
    OPERATOR_LESS = auto()
    OPERATOR_LESS_EQUAL = auto()
    
    
    # Special Simbols
    COLON = auto()
    SEMICOLON = auto()
    COMMA = auto()
    NEWLINE = auto()
    ARROW = auto()
    DOT = auto()
    
    
    # Parens and braces
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    
    
    # Literals
    LITERAL_NUMBER = auto()
    LITERAL_STRING = auto()
    LITERAL_TRUE = auto()
    LITERAL_FALSE = auto()
    LITERAL_IDENT = auto()
    
    # None
    NONE = auto()
    
    # End Of File
    EOF = auto()