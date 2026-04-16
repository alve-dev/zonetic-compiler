from .node_stmt import NodeStmt
from ..param import Param
from ..types import ZonType
from zonc.zonast import BlockExpr
from zonc.location_file import Span

class FuncForm(NodeStmt):
    def __init__(
        self,
        name: str,
        params: list[Param] | None,
        return_type: ZonType,
        block_expr: BlockExpr,
        span_name: Span,
        span: Span,
    ):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.block_expr = block_expr
        self.span_name = span_name
        self.span = span
        
    def get_details(self):
        return f"{self.name}() -> {self.return_type.name}"
    
    def get_children(self):
        children = [self.block_expr]
        if not self.params is None: children.insert(0, self.params)
        return children