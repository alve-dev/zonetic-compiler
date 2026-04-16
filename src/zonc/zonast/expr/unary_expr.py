from .node_expr import NodeExpr
from zonc.location_file import Span
from ..operators import Operator

class UnaryExpr(NodeExpr):
    def __init__(
        self,
        operator: Operator,
        value: NodeExpr,
        span: Span
    ):
        self.operator = operator
        self.value = value
        self.span = span
       
        
    def __repr__(self):
        return f"{__class__.__name__}(operator='{self.operator}', value={self.value})"
    
    def get_children(self):
        return [self.operator, self.value]