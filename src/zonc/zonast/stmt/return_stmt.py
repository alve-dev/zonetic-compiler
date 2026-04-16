from .node_stmt import NodeStmt
from zonc.location_file import Span
from zonc.zonast import NodeExpr

class ReturnStmt(NodeStmt):
    def __init__(
        self,
        value: NodeExpr | None,
        span: Span
    ):
      self.value = value
      self.span = span
      
    def get_children(self):
       return [self.value]