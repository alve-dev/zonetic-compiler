from dataclasses import dataclass
from enum import Enum
from zonc.zonast import ZonType

class RegT(Enum):
    F = 0
    X = 1
    
@dataclass
class ZonVar:
    reg: int
    regt: RegT
    zontype: ZonType

class SymbolTable:
    def __init__(self):
        self.scopes: list[dict[str, ZonVar]] = [{}]
        self.saved = [8, 9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
        self.fsaved = [8, 9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def define(self, name, zontype):
        used_registers = set()
        for scope in self.scopes:
            for var in scope.values():
                if var.regt == RegT.X:
                    used_registers.add(var.reg)

        for r in self.saved:
            if r not in used_registers:
                self.scopes[-1][name] = ZonVar(r, RegT.X, zontype)
                return r
                
        raise Exception(f"Error de registros: No quedan registros 's' disponibles para '{name}'")
    
    def define_f(self, name):
        used_registers = set()
        for scope in self.scopes:
            for var in scope.values():
                if var.regt == RegT.F:
                    used_registers.add(var.reg)

        for r in self.fsaved:
            if r not in used_registers:
                self.scopes[-1][name] = ZonVar(r, RegT.F, ZonType(2, "float"))
                return r
                
        raise Exception(f"Error de registros: No quedan registros 'fs' disponibles para '{name}'")
        
    def resolve(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope.get(name)
            
        raise Exception(f"Variable {name} no definida")
    
    def delete_symbol(self, name):
        del self.scopes[-1][name]
    
    def exists_here(self, name):
        if name in self.scopes[-1]:
            return True
        return False