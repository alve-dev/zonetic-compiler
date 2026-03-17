from enum import Enum, auto

class ErrorCode(Enum):
    # Lexer Errors
    E0001 = auto()
    E0002 = auto()
    E0003 = auto()
    E0004 = auto()
    E0005 = auto()
    
    # Lexer Warnings
    W0001 = auto()
    
    # Normalizer Errors
    E1001 = auto()
    E1002 = auto()
    
    # Parser Errors
    E2001 = auto()
    E2002 = auto()
    E2003 = auto()
    E2004 = auto()
    E2005 = auto()
    E2006 = auto()
    E2007 = auto()
    E2008 = auto()
    E2009 = auto()
    E2010 = auto()
    E2011 = auto()
    
    # Parser Warnings
    W2001 = auto()
    
    # Semantic Errors
    E3001 = auto()
    E3002 = auto()
    E3003 = auto()
    E3004 = auto()
    E3005 = auto()
    E3006 = auto()
    
    # Semantics Warnings
    W3001 = auto()