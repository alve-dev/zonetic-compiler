from .node_stmt import NodeStmt
from .declaration_stmt import DeclarationStmt
from .assignment_stmt import AssignmentStmt
from zonc.location_file import Span

class InitializationStmt(NodeStmt):
    def __init__(
        self,
        decl_stmt: DeclarationStmt,
        assign_stmt: AssignmentStmt,
        span: Span
    ):
        self.decl_stmt = decl_stmt
        self.assign_stmt = assign_stmt
        self.span = span