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
        firma = f"{self.name}("
        if self.params is not None:
            param_len = len(self.params)
            for i, param in enumerate(self.params):
                if i != 0:
                    firma += ", "
                
                if param.mut:
                    firma += "mut "
                else:
                    firma += "inmut "
                    
                firma += param.name
                
                firma += f": {param.zontype.name}"
                
                if param.default is not None:
                    firma += f" = {param.default.value}"
                    
                if i == param_len-1: break
                
        firma += f") -> {self.return_type.name}"
        return firma
    
    def get_children(self):
        children = [self.block_expr]
        return children