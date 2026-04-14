from ..node import Node
from .node_expr import NodeExpr
from zonc.location_file import Span

class CallFunc(Node):
    def __init__(
        self,
        name: str,
        params: list[NodeExpr] | None,
        keyparams: dict[str, tuple[NodeExpr, Span, Span]] | None,
        span: Span,
        span_name: Span
    ):
        self.name = name
        self.params = params
        self.keyparams = keyparams
        self.span = span
        self.span_name = span_name