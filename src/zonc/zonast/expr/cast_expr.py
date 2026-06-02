from .node_expr import NodeExpr
from ..types import ZonType

class CastExpr(NodeExpr):
    def __init__(
        self,
        value: NodeExpr,
        zontype: ZonType, 
        span,
    ):
        self.value = value
        self.zontype = zontype
        self.span = span
        
    def get_details(self):
        match self.zontype.num:
            case 1: return "int64()"
            case 3: return "bool()"
            
    def get_children(self):
        return [self.value]