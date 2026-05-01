from .node import Node
from zonc.location_file import Span

class ErrorNode(Node):
    def __init__(self, span: Span = None):
        super().__init__(span)