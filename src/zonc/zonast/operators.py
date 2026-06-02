from enum import Enum, auto

class Operator(Enum):
    # Arithmetic Binary Operators
    ADD = auto()  # `+`
    SUB = auto()  # `-`
    MUL = auto()  # `*`
    DIV = auto()  # `/`
    POW = auto()  # '**`
    MOD = auto()  # `%`
    
    # Arithmetic Unary Operators
    NEG = auto()  # `-` diferente a SUB, es para unarios y convertir un numero a negativo

    # Boolean Binary Operators
    AND = auto()  # `and` | `&`
    OR = auto()   # `or` | `||`
    
    # Boolean Unary Operators
    NOT = auto()  # `not` | `!`
    
    # Binary Comparison Operators
    EQ = auto()  # `==`
    NE = auto()  # `!=`, NEG + EQ = NE
    
    GT = auto()  # `>`, Greater Than
    LT = auto()  # `<`, Less Than
    
    GE = auto()  # `>=`, Greater or Equal
    LE = auto()  # `<=`, Less or Equal
    
    BAND = auto() # band / &, bitwise and
    BXOR = auto() # bxor / ^, bitwise xor
    BOR = auto() # bor / |, bitwise or
    BNOT = auto() # bnot / ~, bitwise not
    
    SL = auto() # <<, shift left operator
    SR = auto() # >>, shift right operator
    
    CONCAT = auto() # ++, concat operator
    EQ_STR = auto() # ===, eq str operator
    NE_STR = auto() # !==, not eq str operator 
    
    BNAND = auto() # bnand / ~&, bitwise nand
    BXNOR = auto() # bxnor / ~^, bitwise xnor
    BNOR = auto() # bnor / ~|, bitwise nor
    
    def get_details(self):
        match self.value:
            case 1: return '+'
            case 2: return '-'
            case 3: return '*'
            case 4: return '/'
            case 5: return '**'
            case 6: return '%'
            case 7: return '-'
            case 8: return 'and/&&'
            case 9: return 'or/||'
            case 10: return 'not/!'
            case 11: return '=='
            case 12: return '!='
            case 13: return '>'
            case 14: return '<'
            case 15: return '>='
            case 16: return '<='
            case 17: return 'band/&'
            case 18: return 'bxor/^'
            case 19: return 'bor/|'
            case 20: return 'bnot/~'
            case 21: return '<<'
            case 22: return '>>'
            case 23: return '++'
            case 24: return '==='
            case 25: return '!=='
            case 26: return 'bnand/~&'
            case 27: return 'bxnor/~^'
            case 28: return 'bnor/~|'
    