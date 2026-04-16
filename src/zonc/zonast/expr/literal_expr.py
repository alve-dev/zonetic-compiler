from .node_expr import NodeExpr
from zonc.location_file.span import Span

class LiteralNode(NodeExpr):
    pass


class IntLiteral(LiteralNode):
    def __init__(
        self,
        value: int,
        span: Span
        ) -> None:
        
        self.value = value
        self.span = span
        
    def __repr__(self) -> str:
        return f"{__class__.__name__}(value={self.value})"
    

class FloatLiteral(LiteralNode):
    def __init__(
        self,
        value: float,
        span: Span
        ) -> None:
        
        self.value = value
        self.span = span
        
    def __repr__(self) -> str:
        return f"{__class__.__name__}(value={self.value})"


class StringLiteral(LiteralNode):
    def __init__(
        self,
        value: str,
        span: Span
        ) -> None:
        
        self.value = value
        self.span = span
        
    def __repr__(self):
        return f"{__class__.__name__}(value='{self.value}')"

    def get_details(self):
        return self.value.replace('\n', "\\n").replace('\t', "\\t")

class BoolLiteral(LiteralNode):
    def __init__(
        self,
        value: int,
        span: Span
        ) -> None:
        
        self.value = value
        self.span = span
        
    def __repr__(self):
        return f"{__class__.__name__}(value='{self.value}')"