from .node_stmt import NodeStmt
from ..expr.node_expr import NodeExpr
from zonc.location_file import Span

class AssignmentStmt(NodeStmt):
    def __init__(
        self,
        name: str,
        value: NodeExpr,
        span: Span,
        span_name: Span
    ):
        self.name = name
        self.value = value
        self.span = span
        self.span_name = span_name
        
    
    def __repr__(self):
        return f"{__class__.__name__}(name={self.name}, value={self.value})"