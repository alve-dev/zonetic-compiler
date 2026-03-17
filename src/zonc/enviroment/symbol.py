from zonc.ast import ZonType, Node

class Symbol:
    def __init__(
        self,
        mutability: bool,
        zontype: ZonType,
        is_empty
    ):
        self.mutability = mutability
        self.zontype = zontype
        self.is_empty = is_empty
        