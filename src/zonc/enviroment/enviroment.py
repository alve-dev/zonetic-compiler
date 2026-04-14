from zonc.zonast import Node
from typing import Optional
from .symbol import Symbol

class Enviroment:
    def __init__(self, parent: Optional["Enviroment"] = None) -> None:
        self.parent = parent
        self.values: dict[str : Symbol] = {}
    
    
    def define(self, name: str, value: Symbol) -> None:
        self.values[name] = value
        
    
    def get_symbol(self, name: str) -> Symbol | None:
        symbol = self.values.get(name)
        
        if symbol is not None:
            return symbol

        if self.parent:
            return self.parent.get_symbol(name)
        
        return None
    
    
    def assign(self, name: str, new_node: Node) -> bool:
        if name in self.values:
            self.values[name].value = new_node
            return True
        
        if self.parent:
            return self.parent.assign(name, new_node)
        
        return False
    
    
    def exist(self, name: str) -> bool:
        if name in self.values:
            return True
        
        if self.parent:
            return self.parent.exist(name)
        
        return False
    
    def exist_here(self, name: str) -> bool:
        if name in self.values:
            return True
        return False
            
