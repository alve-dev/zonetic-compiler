from .node_expr import NodeExpr
from ..node import Node
from zonc.location_file import Span

class BlockExpr(NodeExpr):
    def __init__(
        self,
        stmts: list[Node],
        give_address: int | None,
        scope,
        span: Span
    ):
        self.stmts = stmts
        self.give_address = give_address
        self.scope = scope
        self.span = span

    
    def __repr__(self):
        return f"{__class__.__name__}"