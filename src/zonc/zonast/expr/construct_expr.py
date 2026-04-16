from .node_expr import NodeExpr
from ..types import ZonType
from zonc.location_file import Span

class ConstructExpr(NodeExpr):
    def __init__(
        self,
        name_struct: str, 
        struct_type: ZonType,
        list_assign: list[NodeExpr] | None,
        dict_assign: dict[str, tuple[NodeExpr, Span, Span]] | None,
        span: Span
    ):
        self.name_struct = name_struct
        self.struct_type = struct_type
        self.list_assign = list_assign
        self.dict_assign = dict_assign
        self.span = span
        
    def get_details(self):
        return f"{self.name_struct}[]"
    
    def get_children(self):
        if not self.dict_assign is None:
            for key, param in self.dict_assign.items():
                self.list_assign.append(param[0])

        return self.list_assign
