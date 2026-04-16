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
    
    def get_details(self):
        return self.name
    