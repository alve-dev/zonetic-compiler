from .node_expr import NodeExpr
from zonc.location_file import Span

class IndexExpr(NodeExpr):
    def __init__(self, name: str, idx_expr: NodeExpr, span: Span):
        self.name = name
        self.idx_expr = idx_expr
        self.span = span

    def get_details(self):
        return self.name + "[]"
    
    def get_children(self):
        return [self.idx_expr]