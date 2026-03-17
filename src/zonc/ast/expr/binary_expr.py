from .node_expr import NodeExpr
from ..operators import Operator
from zonc.location_file import Span

class BinaryExpr(NodeExpr):
    def __init__(
        self,
        left: NodeExpr,
        operator: Operator,
        right: NodeExpr,
        span: Span
    ):
        self.left = left
        self.operator = operator
        self.right = right
        self.span = span
        
    
    def __repr__(self):
        return f"{__class__.__name__}(left={self.left}, operator={self.operator}, right={self.right})"
    