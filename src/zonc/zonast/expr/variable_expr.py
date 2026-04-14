from .node_expr import NodeExpr
from zonc.location_file import Span

class VariableExpr(NodeExpr):
    def __init__(
        self,
        name: str,
        span: Span | None
    ):
        self.name = name
        self.span = span
        
    
    def __repr__(self):
        return f"{__class__.__name__}(name={self.name})"