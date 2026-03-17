from ..node import Node
from zonc.location_file import Span

class PrintStmt(Node):
    def __init__(
        self,
        args: list[Node],
        span: Span
    ):
        self.args = args
        self.span = span
        
        
    def __repr__(self):
        return f"{__class__.__name__}"