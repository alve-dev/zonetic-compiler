from .node_stmt import NodeStmt
from ..expr.node_expr import NodeExpr
from zonc.location_file import Span

class GiveStmt(NodeStmt):
    def __init__(
        self,
        value: NodeExpr,
        span: Span
    ):
        self.value = value
        self.span = span
        
    def __repr__(self):
        return f"{__class__.__name__}(value={self.value})"
    
    def get_children(self):
        return [self.value]