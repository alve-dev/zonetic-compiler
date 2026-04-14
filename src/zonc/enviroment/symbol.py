from zonc.zonast import ZonType
from zonc.location_file import Span
from zonc.zonast import Param

class Symbol:
    def __init__(
        self,
        mutability: bool,
        zontype: ZonType,
        is_empty: bool,
        decl_span: Span,
        scope_object: 'Enviroment' = None,
    ):
        self.mutability = mutability
        self.zontype = zontype
        self.is_empty = is_empty
        self.decl_span = decl_span
        self.scope_object = scope_object
        
class FuncSymbol:
    def __init__(
        self,
        params: list[Param] | None,
        decl_span: Span,
        name_span: Span,
        return_type: ZonType,
        is_native: bool = False,
        is_varidic: bool = False
    ):
        self.params = params
        self.decl_span = decl_span
        self.name_span = name_span
        self.return_type = return_type
        self.is_native = is_native
        self.is_varidic = is_varidic
        