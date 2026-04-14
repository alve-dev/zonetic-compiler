from zonc.location_file import Span

class Node:
    def __init__(self, span: Span):
        self.span = span
    
    def __repr__() -> str:
        return f"<{__class__.__name__}>"