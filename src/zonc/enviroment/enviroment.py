from zonc.zonast import Node
from .symbol import Symbol, FuncSymbol


class Environment:
    """Lexical scope for the semantic analysis and optimization passes.

    Scopes are chained — each Environment holds a reference to its parent
    so that name lookups walk outward through enclosing scopes automatically.
    """

    def __init__(self, parent: "Environment | None" = None) -> None:
        self.parent = parent
        self._symbols: dict[str, Symbol | FuncSymbol] = {}

    # ------------------------------------------------------------------
    # Symbol definition and mutation
    # ------------------------------------------------------------------

    def define(self, name: str, symbol: Symbol | FuncSymbol) -> None:
        self._symbols[name] = symbol

    def assign(self, name: str, new_value: Node) -> bool:
        """Update the value of an existing symbol. Returns False if not found."""
        if name in self._symbols:
            self._symbols[name].value = new_value
            return True

        if self.parent:
            return self.parent.assign(name, new_value)

        return False
    
    def clear(self) -> None:
        self._symbols.clear()

    # ------------------------------------------------------------------
    # Symbol lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Symbol | FuncSymbol | None:
        """Look up a symbol by name, walking parent scopes if needed."""
        symbol = self._symbols.get(name)
        if symbol is not None:
            return symbol

        if self.parent:
            return self.parent.get(name)

        return None

    def exists(self, name: str) -> bool:
        """Return True if the name is defined in this scope or any parent."""
        if name in self._symbols:
            return True

        if self.parent:
            return self.parent.exists(name)

        return False

    def exists_here(self, name: str) -> bool:
        """Return True only if the name is defined in this exact scope."""
        return name in self._symbols

    # ------------------------------------------------------------------
    # Scope introspection
    # ------------------------------------------------------------------

    def collect(self, kind: str, is_field: bool = False) -> list[str]:
        """Return all symbol names of a given kind visible from this scope.

        kind:
            "var"   — plain variables (Symbol)
            "varob" — variables that are struct instances (Symbol with scope_object)
            "fun"   — functions (FuncSymbol)

        is_field: if True, stops at this scope and does not walk to the parent.
        """
        target_type = FuncSymbol if kind == "fun" else Symbol
        names = []

        for name, symbol in self._symbols.items():
            if not isinstance(symbol, target_type):
                continue
            if kind == "varob" and not symbol.scope_object:
                continue
            names.append(name)

        if self.parent and not is_field:
            names.extend(self.parent.collect(kind))

        return names