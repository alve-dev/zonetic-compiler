"""Symbol table and register types for the bytecode emitter.

During code generation each variable is either assigned a physical
s-register (callee-saved, lives for the function's lifetime) or spilled
to a known stack offset. ZonVar holds whichever of those two applies.

The SymbolTable mirrors the lexical scope stack so that name resolution
always finds the innermost binding first.
"""

from dataclasses import dataclass
from enum import Enum
from zonc.zonast import ZonType


class RegT(Enum):
    """Register file selector."""
    F = 0  # float register file
    X = 1  # integer register file


@dataclass
class ZonVar:
    """Represents a variable's location during code generation.

    If reg is not None the variable lives in a physical register.
    If reg is None it has been spilled and offset_stack holds the
    fp-relative byte offset where it lives.

    Global variables use offset_global instead (gp-relative).
    """
    reg:           int | None
    regt:          RegT | None
    zontype:       ZonType
    offset_stack:  int | None = None
    is_global:     bool = False
    offset_global: int | None = None


# ------------------------------------------------------------------
# Symbol table
# ------------------------------------------------------------------

# s-registers available for variable allocation (callee-saved).
_SAVED_X = [9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
_SAVED_F = [8, 9,  18, 19, 20, 21, 22, 23, 24, 25, 26, 27]


class SymbolTable:
    """Lexically scoped symbol table for the bytecode emitter.

    Each scope is a dict mapping name -> ZonVar. Scopes are pushed on
    function/block entry and popped on exit.
    """

    def __init__(self) -> None:
        self._scopes: list[dict[str, ZonVar]] = [{}]

    # ------------------------------------------------------------------
    # Scope management
    # ------------------------------------------------------------------

    def enter_scope(self) -> None:
        self._scopes.append({})

    def exit_scope(self) -> None:
        self._scopes.pop()

    # ------------------------------------------------------------------
    # Definition
    # ------------------------------------------------------------------

    def define_global(self, name: str, offset_global: int, zontype: ZonType) -> None:
        """Register a global variable at a fixed gp-relative offset."""
        self._scopes[-1][name] = ZonVar(
            reg=None, regt=None, zontype=zontype,
            is_global=True, offset_global=offset_global,
        )

    def define(self, name: str, zontype: ZonType) -> ZonVar | None:
        """Assign the next free integer s-register to name.
        Returns the ZonVar on success, None if all s-registers are taken.
        """
        used = {var.reg for scope in self._scopes for var in scope.values() if var.regt == RegT.X}
        for r in _SAVED_X:
            if r not in used:
                var = ZonVar(r, RegT.X, zontype)
                self._scopes[-1][name] = var
                return var
        return None

    def define_f(self, name: str, zontype: ZonType) -> int | None:
        """Assign the next free float s-register to name.
        Returns the physical register number on success, None if all are taken.
        """
        used = {var.reg for scope in self._scopes for var in scope.values() if var.regt == RegT.F}
        for r in _SAVED_F:
            if r not in used:
                self._scopes[-1][name] = ZonVar(r, RegT.F, zontype)
                return r
        return None

    # ------------------------------------------------------------------
    # Lookup and removal
    # ------------------------------------------------------------------

    def resolve(self, name: str) -> ZonVar | None:
        """Find the innermost binding for name, or None."""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def delete_symbol(self, name: str) -> None:
        """Remove name from the innermost scope that defines it."""
        for scope in reversed(self._scopes):
            if name in scope:
                del scope[name]
                return

    def exists(self, name: str) -> bool:
        return any(name in scope for scope in self._scopes)

    def exists_here(self, name: str) -> bool:
        """Return True only if name is defined in the current scope."""
        return name in self._scopes[-1]