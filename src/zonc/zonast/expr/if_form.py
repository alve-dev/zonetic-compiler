from ..node import Node
from zonc.location_file import Span
from .block_expr import BlockExpr
from .node_expr import NodeExpr

class IfBranch:
    def __init__(
        self,
        cond: NodeExpr,
        span: Span,
        block: BlockExpr,
    ):
        self.cond = cond
        self.span = span
        self.block = block
        
    def get_children(self):
        return [self.cond, self.block]

class IfForm(Node):
    def __init__(
        self,
        if_branch: IfBranch,
        elif_branches: list[IfBranch] | None,
        else_branch: IfBranch | None,
        len_branch: int,
        span: Span
    ):
        self.if_branch = if_branch
        self.elif_branches = elif_branches
        self.else_branch = else_branch
        self.len_branch = len_branch
        self.span = span
    
    def __repr__(self):
        return f"{__class__.__name__}"
    
    def get_children(self):
        children = [self.if_branch]
        if not self.elif_branches is None:
            for branch in self.elif_branches:
                children.append(branch)
                
        if not self.else_branch is None:
            children.append(branch)
            
        return children