from .node_expr import NodeExpr
from zonc.location_file import Span
from .block_expr import BlockExpr

class WhileForm(NodeExpr):
    def __init__(
        self,
        condition_field: NodeExpr,
        block_expr: BlockExpr,
        span: Span
    ):
        self.condition_field = condition_field
        self.block_expr  = block_expr
        self.span = span
        
    def __repr__(self):
        return f"{__class__.__name__}(condition_field={self.condition_field})"