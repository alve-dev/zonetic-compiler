from ..node import Node
from zonc.location_file import Span

class NodeExpr(Node):
    def __init__(self, span):
        super().__init__(span)
    