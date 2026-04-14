from .node_expr import NodeExpr
from zonc.location_file import Span
from .variable_expr import VariableExpr


class FieldExpr(NodeExpr):
    def __init__(
        self,
        object_name:'VariableExpr | FieldExpr',
        field: str,
        span: Span
    ):
        self.object_name = object_name
        self.field = field
        self.span = span