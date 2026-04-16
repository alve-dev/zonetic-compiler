from .node import Node

class Program(Node):
    def __init__(
        self,
        stmts: list[Node],
        scope,
        name_file: str
    ):
        self.stmts = stmts
        self.scope = scope
        self.name_file = name_file
    
    def __repr__(self):
        return f"{__class__.__name__}"
    
    def get_details(self):
        return self.name_file
    
    def get_children(self):
        return self.stmts
    