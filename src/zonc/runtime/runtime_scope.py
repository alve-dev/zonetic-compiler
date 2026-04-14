from dataclasses import dataclass, replace
from typing import Any
from zonc.zonast import BlockExpr, Param

@dataclass
class RuntimeValue:
    value: Any
    
@dataclass
class RuntimeFunc:
    block: BlockExpr
    params: list[Param] | None
    
@dataclass
class RuntimeStruct:
    scope_struct: 'RuntimeScope'
    
    def copy(self):
        return replace(self)

class RuntimeScope:
    def __init__(self, parent=None):
        self.values: dict[str, RuntimeValue | RuntimeFunc | RuntimeStruct] = {}
        self.parent = parent
    
    def get(self, name: str) -> RuntimeValue | RuntimeFunc | RuntimeStruct | None:
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        return None
    
    def set(self, name: str, value: RuntimeValue | RuntimeFunc | RuntimeStruct) -> None:
        self.values.update({name: value})
    
    def update(self, name: str, value: Any) -> None:
        if name in self.values:
            self.values[name].value = value
        elif self.parent:
            self.parent.update(name, value)