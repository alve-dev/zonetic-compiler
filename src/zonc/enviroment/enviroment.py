from zonc.zonast import Node
from typing import Optional
from .symbol import Symbol, FuncSymbol

class Enviroment:
    def __init__(self, parent: Optional["Enviroment"] = None) -> None:
        self.parent = parent
        self.values: dict[str, Symbol] = {}
    
    
    def define(self, name: str, value: Symbol) -> None:
        self.values[name] = value
        
    
    def get_symbol(self, name: str) -> Symbol | FuncSymbol | None:
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
    
    def get_values_valids(self, type_symbol: str, is_field: bool = False) -> list:
        symbol = None
        list_symbols = []
        if type_symbol == "var" or type_symbol == "varob": symbol = Symbol
        elif type_symbol == "fun": symbol = FuncSymbol
        
        for key, sym in self.values.items():
            if isinstance(sym, symbol):
                if type_symbol == "varob":
                    if sym.scope_object:
                        list_symbols.append(key)
                else:
                    list_symbols.append(key)
                     
        if self.parent and not is_field:
            list_symbols.extend(self.parent.get_values_valids(type_symbol))
            
        return list_symbols
            
