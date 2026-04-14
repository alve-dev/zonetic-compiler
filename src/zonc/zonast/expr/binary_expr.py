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
    