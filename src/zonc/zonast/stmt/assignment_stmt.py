from .node_stmt import NodeStmt
from ..expr.node_expr import NodeExpr
from zonc.location_file import Span
from ..expr.index_expr import IndexExpr

class AssignmentStmt(NodeStmt):
    def __init__(
        self,
        target: str | IndexExpr,
        value: NodeExpr,
        span: Span,
        span_name: Span
    ):
        self.target = target
        self.value = value
        self.span = span
        self.span_name = span_name
        
    
    def __repr__(self):
        return f"{__class__.__name__}(name={self.name}, value={self.value})"
    
    def get_details(self):
        if isinstance(self.target, str):
            return self.target
        
        elif isinstance(self.target, IndexExpr):
            return self.target.name + "[]"
    
    def get_children(self):
        return [self.value]