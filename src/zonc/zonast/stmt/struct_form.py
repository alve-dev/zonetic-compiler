from .node_stmt import NodeStmt
from ..expr.block_expr import BlockExpr
from zonc.location_file import Span
from ..types import ZonType

class StructForm(NodeStmt):
    def __init__(
        self,
        name: str,
        block_expr: BlockExpr,
        zontype: ZonType,
        span: Span,
        span_name: Span
    ):
        self.name = name
        self.block_expr = block_expr
        self.span = span
        self.span_name = span_name
        self.zontype = zontype