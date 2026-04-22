class SymbolTable:
    def __init__(self):
        self.scopes = [{}]
        self.saved = [8, 9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]

    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def define(self, name):
        used_registers = set()
        for scope in self.scopes:
            used_registers.update(scope.values())

        for r in self.saved:
            if r not in used_registers:
                self.scopes[-1][name] = r
                return r
                
        raise Exception(f"Error de registros: No quedan registros 's' disponibles para '{name}'")

    def resolve(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope.get(name)
        raise Exception(f"Variable {name} no definida")
    
    def exists_here(self, name):
        if name in self.scopes[-1]:
            return True
        return False