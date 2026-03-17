from ..node import Node
from zonc.location_file import Span
from ..types import ZonType

class InputExpr(Node):
    def __init__(
        self,
        zontype: ZonType,
        prompt: str,
        span: Span
    ):
        self.zontype = zontype
        self.prompt = prompt
        self.span = span
        