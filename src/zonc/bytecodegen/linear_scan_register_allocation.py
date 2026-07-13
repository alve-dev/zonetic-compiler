"""Linear scan register allocation pre-analysis.

This is not a full linear scan allocator — it is a single-pass analysis
that walks the AST before code generation to answer two questions:

  1. How many bytes does this function's stack frame need?
  2. Which s-registers (callee-saved) will the function use?

The results are consumed by the prologue/epilogue emitters in func_gen.py.

How the frame size is calculated
---------------------------------
  bytes_needed = (spilled_vars * 8) + (spilled_temps * 8) + 16 + array_bytes + caller_save_bytes

  - spilled_vars:       integer/float variables that exceed the s-register budget
  - spilled_temps:      temporary registers that exceed the t-register budget
  - 16:                 always reserved for s0 (frame pointer) and ra (if has_call)
  - array_bytes:        stack space allocated explicitly for static arrays
  - caller_save_bytes:  stack space reserved for saving live temporaries around function calls

The result is rounded up to the next 16-byte boundary (ABI alignment).
"""

from zonc.zonast import *


# s-registers available for integer and float variables respectively.
# These are callee-saved, so the prologue saves them and the epilogue
# restores them. The lists are ordered by preference.
_SAVED_X = [9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
_SAVED_F = [8, 9,  18, 19, 20, 21, 22, 23, 24, 25, 26, 27]


class LinearScanRegisterAllocation:

    def __init__(self, num_available_regs: int = 5, num_available_fregs: int = 10) -> None:
        self._num_regs  = num_available_regs
        self._num_fregs = num_available_fregs

        # current live temp count and peak (reset per analysis)
        self._cur_regs  = 0
        self._cur_fregs = 0
        self._max_regs  = 0
        self._max_fregs = 0

        # variable names seen during the scan
        self._seen_ints:   set[str] = set()
        self._seen_floats: set[str] = set()

        self.has_call  = False
        self.used_heap = False
        
        # Explicitly separated stack space metrics
        self.array_bytes       = 0  # Space allocated for stack arrays
        self.caller_save_bytes = 0  # Space needed to shield live temporaries across calls

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze_function(self, stmts: list, params: list = None) -> tuple:
        """Analyze stmts and return frame layout information.

        Returns:
            (bytes_needed, has_call, (used_save_x, used_save_f), used_heap)
        """
        self._reset()

        if params is not None:
            for param in params:
                self._register_var(param.name, param.zontype.num)

        # Pre-calculate explicit array allocations upfront
        self.array_bytes = self._get_array_space(stmts)

        # Walk the AST to simulate register pressure and identify function calls
        self._scan_list(stmts)

        # variables that don't fit in s-registers spill to the stack
        extra_ints   = max(0, len(self._seen_ints)   - len(_SAVED_X))
        extra_floats = max(0, len(self._seen_floats) - len(_SAVED_F))

        # temps that don't fit in t-registers also spill
        temp_spill  = max(0, self._max_regs  - self._num_regs)
        ftemp_spill = max(0, self._max_fregs - self._num_fregs)

        total_slots  = extra_ints + extra_floats + temp_spill + ftemp_spill
        
        # Now calculating frame layout cleanly with separate properties
        bytes_needed = (total_slots * 8) + 16 + self.array_bytes + self.caller_save_bytes

        # RISC-V ABI requires 16-byte stack alignment
        if bytes_needed % 16 != 0:
            bytes_needed += 16 - (bytes_needed % 16)

        used_save_x = _SAVED_X[:min(len(self._seen_ints),   len(_SAVED_X))]
        used_save_f = _SAVED_F[:min(len(self._seen_floats), len(_SAVED_F))]

        return bytes_needed, self.has_call, (used_save_x, used_save_f), self.used_heap

    def _get_array_space(self, stmts: list) -> int:
        """Return total bytes needed for stack arrays declared in stmts.
        Recurses into blocks, if forms, and while forms — but not FuncForms,
        which have their own frame.
        """
        total = 0
        for stmt in stmts:
            if isinstance(stmt, DeclarationStmt) and stmt.type.size is not None:
                if isinstance(stmt.type.size, IntLiteral):
                    total += 8 * stmt.type.size.value

            elif isinstance(stmt, WhileForm):
                total += self._get_array_space(stmt.block_expr.stmts)

            elif isinstance(stmt, IfForm):
                if stmt.if_branch:
                    total += self._get_array_space(stmt.if_branch.block.stmts)
                if stmt.elif_branches:
                    for b in stmt.elif_branches:
                        total += self._get_array_space(b.block.stmts)
                if stmt.else_branch:
                    total += self._get_array_space(stmt.else_branch.block.stmts)

            elif isinstance(stmt, BlockExpr):
                total += self._get_array_space(stmt.stmts)

        return total

    # ------------------------------------------------------------------
    # Internal reset
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        self._cur_regs  = 0
        self._cur_fregs = 0
        self._max_regs  = 0
        self._max_fregs = 0
        self._seen_ints.clear()
        self._seen_floats.clear()
        self.has_call          = False
        self.used_heap         = False
        self.array_bytes       = 0
        self.caller_save_bytes = 0

    # ------------------------------------------------------------------
    # Variable registration helper
    # ------------------------------------------------------------------

    def _register_var(self, name: str, type_num: int) -> None:
        """Add a variable to the appropriate seen-set based on its type."""
        if type_num in (1, 3, 6):
            self._seen_ints.add(name)
        elif type_num in (2, 7):
            self._seen_floats.add(name)

    # ------------------------------------------------------------------
    # Temp register simulation
    # ------------------------------------------------------------------

    def _alloc_t(self) -> None:
        self._cur_regs += 1
        if self._cur_regs > self._max_regs:
            self._max_regs = self._cur_regs

    def _free_t(self) -> None:
        self._cur_regs = max(0, self._cur_regs - 1)

    def _alloc_ft(self) -> None:
        self._cur_fregs += 1
        if self._cur_fregs > self._max_fregs:
            self._max_fregs = self._cur_fregs

    def _free_ft(self) -> None:
        self._cur_fregs = max(0, self._cur_fregs - 1)

    # ------------------------------------------------------------------
    # AST scanner
    # ------------------------------------------------------------------

    def _scan_list(self, nodes: list) -> None:
        if not nodes:
            return
        for node in nodes:
            self._scan_node(node)

    def _scan_node(self, node) -> None:
        if node is None:
            return

        match node:

            case FuncForm():
                if node.params is not None:
                    for param in node.params:
                        self._register_var(param.name, param.zontype.num)

            case InitializationStmt():
                self._scan_node(node.assign_stmt.value)
                if node.decl_stmt.name not in self._seen_ints and node.decl_stmt.name not in self._seen_floats:
                    self._register_var(node.decl_stmt.name, node.decl_stmt.type.num)

            case DeclarationStmt():
                if node.type.size is not None:
                    return
                if node.name not in self._seen_ints and node.name not in self._seen_floats:
                    self._register_var(node.name, node.type.num)

            case AssignmentStmt():
                self._scan_node(node.value)
                if isinstance(node.target, IndexExpr): self._scan_node(node.target.idx_expr)

            case CastExpr():
                self._scan_node(node.value)
                if node.zontype.num in (2, 7):
                    self._free_ft(); self._alloc_ft()
                else:
                    self._free_t();  self._alloc_t()

            case BinaryExpr():
                self._scan_binary(node)

            case IndexExpr():
                self._scan_node(node.idx_expr)

            case UnaryExpr():
                self._scan_node(node.value)
                if node.operator == Operator.NEG and isinstance(node.value, FloatLiteral):
                    self._free_ft(); self._alloc_ft()
                else:
                    self._free_t();  self._alloc_t()

            case CallFunc():
                self._scan_call(node)

            case IfForm():
                if node.if_branch:
                    self._scan_node(node.if_branch.cond)
                    self._scan_node(node.if_branch.block)
                if node.elif_branches:
                    for branch in node.elif_branches:
                        self._scan_node(branch.cond)
                        self._scan_node(branch.block)
                if node.else_branch:
                    self._scan_node(node.else_branch.block)

            case BlockExpr():
                self._scan_list(node.stmts)

            case WhileForm():
                self._scan_node(node.condition_field)
                self._scan_node(node.block_expr)

            case GiveStmt() | ReturnStmt():
                self._scan_node(node.value)
                if isinstance(node.value, FloatLiteral):
                    self._free_ft()
                else:
                    self._free_t()

            case IntLiteral() | BoolLiteral():
                self._alloc_t()
                self._alloc_t()
                self._free_t()

            case FloatLiteral():
                self._alloc_ft()
                self._alloc_t()
                self._free_t()

            case StringLiteral():
                self._alloc_t()
                self._free_t()

    def _scan_binary(self, node: BinaryExpr) -> None:
        """Simulate register usage for a binary expression."""
        _BITWISE_OPS = (
            Operator.CONCAT, Operator.EQ_STR, Operator.NE_STR,
            Operator.BNAND, Operator.BNOR, Operator.BXNOR,
        )
        _CMP_OPS = (Operator.LT, Operator.GT, Operator.LE, Operator.GE, Operator.EQ, Operator.NE)

        if node.operator in _BITWISE_OPS:
            self._scan_node(node.left)
            self._scan_node(node.right)
            self._free_t(); self._free_t(); self._alloc_t()
            if node.operator == Operator.CONCAT:
                self.used_heap = True
            return

        # add/sub with a small immediate: only one side needs a register
        if node.operator in (Operator.ADD, Operator.SUB):
            if isinstance(node.right, IntLiteral) and -2048 <= node.right.value <= 2047:
                self._scan_node(node.left)
                self._alloc_t()
                return
            if isinstance(node.left, IntLiteral) and -2048 <= node.left.value <= 2047:
                self._scan_node(node.right)
                self._alloc_t()
                return

        self._scan_node(node.left)
        self._scan_node(node.right)

        uses_float = isinstance(node.left, FloatLiteral) or isinstance(node.right, FloatLiteral)

        if node.operator in _CMP_OPS:
            if uses_float:
                self._free_ft(); self._free_ft()
            else:
                self._free_t(); self._free_t()
            self._alloc_t()
        else:
            if uses_float:
                self._free_ft(); self._free_ft(); self._alloc_ft()
            else:
                self._free_t(); self._free_t(); self._alloc_t()

    def _scan_call(self, node: CallFunc) -> None:
        """Simulate register usage around a function call."""
        _HEAP_BUILTINS = {"alloc", "store", "load"}
        _ALL_BUILTINS  = {"print", "println"} | _HEAP_BUILTINS

        if node.name not in _ALL_BUILTINS:
            self.has_call = True
            # Accumulate caller-save memory explicitly based on currently active temporaries
            self.caller_save_bytes += (self._cur_regs * 8) + (self._cur_fregs * 8)

        if node.name in _HEAP_BUILTINS:
            self.used_heap = True

        if node.params is not None:
            for param in node.params:
                self._scan_node(param)

            for param in node.params:
                if isinstance(param, FloatLiteral):
                    self._free_ft()
                else:
                    self._free_t()

        # one slot for the return value (int and float register)
        self._alloc_t()
        self._alloc_ft()