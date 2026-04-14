from .node_stmt import NodeStmt
from ..types import ZonType
from zonc.location_file import Span

class DeclarationStmt(NodeStmt):
    def __init__(
        self,
        name: str,
        mut: bool,
        type: ZonType,
        span_name: Span,
        span: Span,
    ):
        self.name = name
        self.mut = mut
        self.type = type
        self.span_name = span_name
        self.span = span
        
    
    def __repr__(self):
        return f"{__class__.__name__}(name={self.name}, type={self.type})"