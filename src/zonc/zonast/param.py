from zonc.zonast import ZonType
from .expr.node_expr import NodeExpr
from zonc.location_file import Span

class Param:
    def __init__(
        self,
        mut: bool,
        name: str,
        zontype: ZonType,
        default: NodeExpr | None,
        span: Span,
        span_name: Span
    ):
        self.mut = mut
        self.name = name
        self.zontype = zontype
        self.default = default
        self.span = span
        self.span_name = span_name
        
    def get_details(self):
        mut_str = "mut" if self.mut else "inmut"
        return f"{mut_str} {self.name}: {self.zontype.name}"
    
    def get_children(self):
        return [self.default]