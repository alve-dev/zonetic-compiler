"""Register manager for temporary registers during code generation.

Tracks which t-registers (temporaries) are currently in use and handles
spilling to the stack when all physical registers are occupied.

Register conventions
---------------------
Integer temps:  t0=5, t1=6, t2=7, t3=28, t4=29   (x31/t6 is scratch, never allocated)
Float temps:    ft0-ft7=0-7, ft8=28, ft9=29        (f31/ft11 is scratch, never allocated)

When all temps are occupied, the manager spills to the frame's spill area
and tracks freed spill slots for reuse before carving new ones.
"""

from .bytecodescope import ZonVar, RegT
from zonc.zonast import ZonType

_UNKNOWN_TYPE = ZonType(0, "UNKNOWN")


class RegisterManager:
    def __init__(self, offset_stack: list) -> None:
        self._temps  = [5, 6, 7, 28, 29]
        self._ftemps = [0, 1, 2, 3, 4, 5, 6, 7, 28, 29]

        # True means available, False means in use
        self._free_temps  = [True] * len(self._temps)
        self._free_ftemps = [True] * len(self._ftemps)

        self._offset_stack       = offset_stack
        self._recycled_spills: list[int] = []

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def alloc_temp(self) -> ZonVar:
        """Allocate an integer temporary. Spills to stack if none are free."""
        for i, available in enumerate(self._free_temps):
            if available:
                self._free_temps[i] = False
                return ZonVar(self._temps[i], RegT.X, _UNKNOWN_TYPE)

        return ZonVar(None, RegT.X, _UNKNOWN_TYPE, self._alloc_spill_slot())

    def alloc_ftemp(self) -> ZonVar:
        """Allocate a float temporary. Spills to stack if none are free."""
        for i, available in enumerate(self._free_ftemps):
            if available:
                self._free_ftemps[i] = False
                return ZonVar(self._ftemps[i], RegT.F, _UNKNOWN_TYPE)

        return ZonVar(None, RegT.F, _UNKNOWN_TYPE, self._alloc_spill_slot())

    # ------------------------------------------------------------------
    # Deallocation
    # ------------------------------------------------------------------

    def free_temp(self, reg: ZonVar) -> None:
        """Return a temporary register (or spill slot) to the free pool."""
        if reg.reg is None:
            self._recycled_spills.append(reg.offset_stack)
            return

        regs  = self._temps  if reg.regt == RegT.X else self._ftemps
        flags = self._free_temps if reg.regt == RegT.X else self._free_ftemps

        for i, r in enumerate(regs):
            if r == reg.reg:
                flags[i] = True
                break

    # ------------------------------------------------------------------
    # Caller-save introspection
    # ------------------------------------------------------------------

    def get_active_regs(self) -> tuple[list[int], list[int]]:
        """Return (active_int_regs, active_float_regs) — registers currently in use.
        Used by the call emitter to know which temps need to be saved around a call.
        """
        active_x = [r for r, free in zip(self._temps,  self._free_temps)  if not free]
        active_f = [r for r, free in zip(self._ftemps, self._free_ftemps) if not free]
        return active_x, active_f

    # ------------------------------------------------------------------
    # Spill slot management
    # ------------------------------------------------------------------

    def _alloc_spill_slot(self) -> int:
        """Return a stack offset for a spilled temporary.
        Reuses a previously freed slot when available; otherwise carves
        a new 8-byte slot from the frame's spill area.
        """
        if self._recycled_spills:
            return self._recycled_spills.pop()

        frame = self._offset_stack[-1]
        
        bytes_needed = frame.bytes_needed
        current_ptr  = frame.spill_ptr
        
        fp_offset    = -(bytes_needed - current_ptr)
        
        frame.spill_ptr -= 8
        frame[0]         = frame.spill_ptr
        
        return fp_offset