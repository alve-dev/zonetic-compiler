from .node_stmt import NodeStmt
from zonc.location_file import Span
from .assignment_stmt import AssignmentStmt
from ..expr.field_expr import FieldExpr
from ..expr.variable_expr import VariableExpr

class AssignmentFieldStmt(NodeStmt):
    def __init__(
        self,
        object_name: 'FieldExpr | VariableExpr',
        field_assign: AssignmentStmt,
        span: Span
    ):
        self.object_name = object_name
        self.field_assign = field_assign
        self.span = span
