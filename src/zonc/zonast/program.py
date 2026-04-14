from .node import Node

class Program(Node):
    def __init__(
        self,
        stmts: list[Node],
        scope
    ):
        self.stmts = stmts
        self.scope = scope
    
    
    def __repr__(self):
        return f"{__class__.__name__}"
    