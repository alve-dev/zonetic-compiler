from .node_stmt import NodeStmt
from zonc.location_file import Span

class ContinueStmt(NodeStmt):
    def __init__(
        self,
        span: Span
    ):
        self.span = span
    
    
    def __repr__(self):
        return f"{__class__.__name__}"