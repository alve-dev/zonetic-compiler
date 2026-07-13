"""Constant folding optimization pass.

Walks the AST before code generation and evaluates expressions whose
values are fully known at compile time, replacing them with literals.
This lets the emitter see simple loads instead of arithmetic chains,
and also catches divide-by-zero and overflow before runtime.

Only immutable variables are inlined — mutable ones are left alone
because their value can change between the fold pass and execution.
"""

import math
import struct

from zonc.zonast import *
from zonc.enviroment import Environment, Symbol, FuncSymbol
from zonc.zonc_errors import DiagnosticEngine, ErrorCode


# Integer range limits used for overflow checking.
_INT_RANGES = {
    "int32": (-2_147_483_648, 2_147_483_647),
    "int64": (-9_223_372_036_854_775_808, 9_223_372_036_854_775_807),
}

# Mask for keeping shift results within 64 bits.
_U64_MASK  = 0xFFFF_FFFF_FFFF_FFFF
_I64_SIGN  = 0x8000_0000_0000_0000
_I64_RANGE = 0x1_0000_0000_0000_0000


class ConstantFolding:
    """Folds constant expressions in-place across the whole AST."""

    def __init__(self, diag: DiagnosticEngine) -> None:
        self._diag = diag

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def visit_Program(self, node: Program | BlockExpr, top_level: bool = False) -> None:
        """Fold every statement in a program or block node."""
        scope: Environment = node.scope
        scope.clear()

        if top_level:
            self._pre_scan(node, scope)

        for stmt in node.stmts:
            if isinstance(stmt, DeclarationStmt):
                if stmt.type.size is not None:
                    size_folded = self._to_node(self._eval(stmt.type.size, scope))
                    
                    if not isinstance(size_folded, IntLiteral):
                        self._diag.emit(
                            ErrorCode.E5006, None, [stmt.span], [(stmt.type.size.span, "It is not an integer or a constant variable.")]
                        )
                        continue
                    
                    else:
                        stmt.type.size = size_folded

                scope.define(stmt.name, Symbol(stmt.mut, stmt.type, True, stmt.span))

            elif isinstance(stmt, AssignmentStmt):
                self._fold_assignment(stmt, scope)

            elif isinstance(stmt, InitializationStmt):
                self._fold_initialization(stmt, scope)

            elif isinstance(stmt, BlockExpr):
                self.visit_Program(stmt)

            elif isinstance(stmt, IfForm):
                self._fold_if(stmt, scope)
                self.visit_Program(stmt.if_branch.block)
                if stmt.elif_branches is not None:
                    for branch in stmt.elif_branches:
                        self.visit_Program(branch.block)
                if stmt.else_branch is not None:
                    self.visit_Program(stmt.else_branch.block)

            elif isinstance(stmt, GiveStmt):
                folded = self._eval(stmt.value, scope)
                stmt.value = self._to_node(folded)
                return folded

            elif isinstance(stmt, CallFunc):
                self._fold_call(stmt, scope)

            elif isinstance(stmt, FuncForm):
                self.visit_Program(stmt.block_expr)

            elif isinstance(stmt, WhileForm):
                cond_folded = self._to_node(self._eval(stmt.condition_field, scope))
                stmt.condition_field = cond_folded

            else:
                return None

    # ------------------------------------------------------------------
    # Pre-scan: register functions and their params before folding bodies
    # ------------------------------------------------------------------

    def _pre_scan(self, node: Program, scope: Environment) -> None:
        """Register all top-level functions so calls inside them can be folded."""
        for stmt in node.stmts:
            if not isinstance(stmt, FuncForm):
                continue

            # void functions always need an explicit return at the end
            if stmt.return_type.num == 5:
                stmt.block_expr.stmts.append(ReturnStmt(None, None))

            if stmt.params is not None:
                for param in stmt.params:
                    scope.define(param.name, Symbol(param.mut, param.zontype, True, param.span))

            scope.define(stmt.name, FuncSymbol(stmt.params, stmt.span, stmt.span_name, stmt.return_type))

    # ------------------------------------------------------------------
    # Statement visitors
    # ------------------------------------------------------------------

    def _fold_if(self, node: IfForm, scope: Environment) -> None:
        """Fold the condition of every branch in an if form."""
        node.if_branch.cond = self._to_node(self._eval(node.if_branch.cond, scope))

        if node.elif_branches is not None:
            for i, branch in enumerate(node.elif_branches):
                node.elif_branches[i].cond = self._to_node(self._eval(branch.cond, scope))

    def _fold_initialization(self, node: InitializationStmt, scope: Environment) -> None:
        """Fold the right-hand side of a declaration+assignment and store the result."""
        span   = node.assign_stmt.value.span
        folded = self._eval(node.assign_stmt.value, scope, in_var=True)

        # folded can be (original_expr, folded_value) when the expr is compound
        if isinstance(folded, tuple):
            literal = self._to_node(folded[1])
            new_value = folded[0]
        else:
            literal = self._to_node(folded)
            new_value = literal

        literal.span = span

        symbol = Symbol(node.decl_stmt.mut, node.decl_stmt.type, False, node.decl_stmt.span)
        scope.define(node.decl_stmt.name, symbol)

        self._apply_folded(node.assign_stmt, symbol, literal, new_value, span, target="value")

    def _fold_assignment(self, node: AssignmentStmt, scope: Environment) -> None:
        """Fold the right-hand side of a plain assignment."""
        span   = node.value.span
        is_array = isinstance(node.target, IndexExpr)
        folded = self._eval(node.value, scope, in_var=True)

        if isinstance(folded, tuple):
            literal = self._to_node(folded[1])
            new_value = folded[0]
        else:
            literal = self._to_node(folded)
            new_value = literal

        literal.span = span
        symbol = None

        if is_array:
            symbol = scope.get(node.target.name)
            idx_folded = self._to_node(self._eval(node.target.idx_expr, scope))
            if isinstance(idx_folded, IntLiteral) and isinstance(symbol.zontype.size, IntLiteral):
                self._check_index(idx_folded.value, symbol.zontype.size.value, node.target.idx_expr.span)

            node.target.idx_expr = idx_folded

        else:
            symbol = scope.get(node.target)

        self._apply_folded(node, symbol, literal, new_value, span, target="value")

    def _apply_folded(self, node, symbol: Symbol, literal, new_value, span, target: str) -> None:
        """Write the folded value back into node and update the symbol table."""
        if isinstance(literal, IntLiteral):
            if symbol.zontype.num in (1, 6):
                if self._check_int_range(literal.value, symbol.zontype.name, span):
                    return
            setattr(node, target, new_value)
            symbol.value = literal

        elif isinstance(literal, FloatLiteral):
            if symbol.zontype.num in (2, 7):
                if self._check_float_range(literal.value, symbol.zontype.name, span):
                    return
            setattr(node, target, new_value)
            symbol.value = literal

        elif isinstance(literal, BoolLiteral):
            setattr(node, target, new_value)
            symbol.value = literal

        elif isinstance(literal, CallFunc):
            return  # cannot fold a call result at compile time

        else:
            setattr(node, target, new_value)
            symbol.value = literal

    def _fold_call(self, node: CallFunc, scope: Environment) -> None:
        """Resolve keyword-params to positional, then fold each argument."""
        self._resolve_keyparams(node, scope)

        if node.params is None:
            return

        for i, param in enumerate(node.params):
            span   = param.span
            folded = self._eval(param, scope, in_var=True)
            result = self._to_node(folded)
            result.span = span

            if isinstance(result, IntLiteral):
                if not self._check_int_range(result.value, "int64", span):
                    node.params[i] = result
            elif isinstance(result, FloatLiteral):
                if not self._check_float_range(result.value, "double", span):
                    node.params[i] = result
            else:
                node.params[i] = result

    def _resolve_keyparams(self, node: CallFunc, scope: Environment) -> None:
        """Reorder keyword arguments to match the positional parameter list.

        After this, node.params is a plain positional list and node.keyparams
        is consumed. Builtins that accept variadic args are skipped.
        """
        _VARIADIC_BUILTINS = {"print", "println", "alloc", "store", "load"}
        if node.name in _VARIADIC_BUILTINS:
            return

        if node.params is None:
            return

        func = scope.get(node.name)
        ordered = [0] * len(func.params)

        for i, param in enumerate(node.params):
            ordered[i] = param

        if node.keyparams is not None:
            for key, (val_expr, _span, _key_span) in node.keyparams.items():
                for i, param in enumerate(func.params):
                    if key == param.name:
                        ordered[i] = val_expr
                        break

        node.params = ordered

    # ------------------------------------------------------------------
    # Core evaluator
    # ------------------------------------------------------------------

    def _eval(self, node, scope: Environment, in_var: bool = False):
        """Recursively evaluate node to a Python value if possible.

        Returns a Python int/float/bool/str when the value is known,
        or the original AST node when it cannot be determined at compile time.
        A (original_node, python_value) tuple is returned from BinaryExpr
        when only one side could be folded — the original node is kept for
        the emitter but the python value is used for further folding.
        """
        match node:

            case BinaryExpr():
                return self._eval_binary(node, scope, in_var)

            case IntLiteral():
                if in_var:
                    return node.value
                if self._check_int_range(node.value, "int64", node.span):
                    return node
                return node.value

            case FloatLiteral():
                if math.isinf(node.value):
                    sign = "inf" if node.value > 0 else "-inf"
                    self._diag.emit(
                        ErrorCode.E5005,
                        {"target_type": "double", "max_val": "1.79e308", "inf": sign},
                        [node.span], [(node.span, "value exceeds {target_type} range")],
                    )
                    return node
                if in_var:
                    return node.value
                if self._check_float_range(node.value, "double", node.span):
                    return node
                return node.value

            case BoolLiteral():
                return bool(node.value)

            case StringLiteral():
                return node.value

            case VariableExpr():
                symbol = scope.get(node.name)
                if not symbol.mutability and not symbol.is_empty and symbol.value is not None:
                    return self._eval(symbol.value, scope, in_var)
                return node

            case UnaryExpr():
                val = self._eval(node.value, scope, in_var)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    if node.operator == Operator.NEG:  return -val
                    if node.operator == Operator.BNOT: return ~val
                if isinstance(val, bool) and node.operator == Operator.NOT:
                    return not val
                node.value = self._to_node(val)
                return node

            case CastExpr():
                return self._eval_cast(node, scope, in_var)
            
            case IndexExpr():
                idx_folded = self._to_node(self._eval(node.idx_expr, scope))
                symbol = scope.get(node.name)
                if isinstance(idx_folded, IntLiteral) and isinstance(symbol.zontype.size, IntLiteral):
                    self._check_index(idx_folded.value, symbol.zontype.size.value, node.idx_expr.span)

                node.idx_expr = idx_folded

                return node

            case BlockExpr():
                self.visit_Program(node)
                return node

            case IfForm():
                self._fold_if(node, scope)
                self.visit_Program(node.if_branch.block)
                if node.elif_branches is not None:
                    for branch in node.elif_branches:
                        self.visit_Program(branch.block)
                if node.else_branch is not None:
                    self.visit_Program(node.else_branch.block)
                return node

            case CallFunc():
                self._fold_call(node, scope)
                return node

            case _:
                return node

    # ------------------------------------------------------------------
    # Binary expression evaluation
    # ------------------------------------------------------------------

    def _eval_binary(self, node: BinaryExpr, scope: Environment, in_var: bool):
        left  = self._eval(node.left,  scope, in_var)
        right = self._eval(node.right, scope, in_var)

        is_num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)

        if is_num(left) and is_num(right):
            try:
                result = self._apply_numeric_op(node, left, right)
                if result is not node:
                    return result
            except OverflowError:
                return float("inf")

        elif isinstance(left, bool) and isinstance(right, bool):
            result = self._apply_bool_op(node, left, right)
            if result is not node:
                return result

        elif isinstance(left, str) and isinstance(right, str):
            result = self._apply_str_op(node, left, right)
            if result is not node:
                return result

        # partial fold: update children even if the whole expr can't be reduced
        node.left  = self._to_node(left)
        node.right = self._to_node(right)
        return node

    def _apply_numeric_op(self, node: BinaryExpr, left, right):
        op = node.operator
        match op:
            case Operator.ADD: return left + right
            case Operator.SUB: return left - right
            case Operator.MUL: return left * right

            case Operator.DIV:
                if right == 0:
                    if isinstance(left, float):
                        sign = "+Inf" if left > 0 else "-Inf"
                        self._diag.emit(ErrorCode.E5002, {"inf": sign}, [node.span],
                            [(node.span, "this division results in an infinite value")])
                    else:
                        self._diag.emit(ErrorCode.E5001, None, [node.span],
                            [(node.right.span, "constant folding evaluated this divisor to zero")])
                    return node
                return left / right

            case Operator.MOD:
                if right == 0:
                    self._diag.emit(ErrorCode.E5001, None, [node.span],
                        [(node.right.span, "constant folding evaluated this divisor to zero")])
                    return node
                return math.fmod(left, right) if isinstance(left, float) else left % right

            case Operator.LT:  return left < right
            case Operator.GT:  return left > right
            case Operator.LE:  return left <= right
            case Operator.GE:  return left >= right
            case Operator.EQ:  return left == right
            case Operator.NE:  return left != right

            case Operator.BAND:  return left & right
            case Operator.BXOR:  return left ^ right
            case Operator.BOR:   return left | right
            case Operator.BNAND: return ~(left & right)
            case Operator.BXNOR: return ~(left ^ right)
            case Operator.BNOR:  return ~(left | right)

            case Operator.SL | Operator.SR:
                return self._eval_shift(node, left, right)

            # TODO: add Operator.POW when the emitter supports it

        return node

    def _eval_shift(self, node: BinaryExpr, left: int, right: int):
        if right < 0 or right > 63:
            print("error temporal de shift")
            return node

        if node.operator == Operator.SL:
            result = (left << right) & _U64_MASK
            return result - _I64_RANGE if result >= _I64_SIGN else result

        # arithmetic right shift (sign-extending)
        signed = left if left < 0 else (left - _I64_RANGE if left & _I64_SIGN else left)
        result = (signed >> right) & _U64_MASK
        return result - _I64_RANGE if result >= _I64_SIGN else result

    def _apply_bool_op(self, node: BinaryExpr, left: bool, right: bool):
        match node.operator:
            case Operator.AND: return left and right
            case Operator.OR:  return left or right
            case Operator.EQ:  return left == right
            case Operator.NE:  return left != right
        return node

    def _apply_str_op(self, node: BinaryExpr, left: str, right: str):
        match node.operator:
            case Operator.CONCAT: return left + right
            case Operator.EQ_STR: return left == right
            case Operator.NE_STR: return left != right
        return node

    # ------------------------------------------------------------------
    # Cast expression evaluation
    # ------------------------------------------------------------------

    def _eval_cast(self, node: CastExpr, scope: Environment, in_var: bool):
        val = self._eval(node.value, scope, in_var)

        if node.zontype.num == 1:   # int64
            if isinstance(val, bool): return 1 if val else 0
            if isinstance(val, int):  return val
            return node

        if node.zontype.num == 3:   # bool
            if isinstance(val, bool): return val
            if isinstance(val, int):  return val != 0
            return node

        return node

    # ------------------------------------------------------------------
    # Value ↔ AST node conversion
    # ------------------------------------------------------------------

    def _to_node(self, value) -> NodeExpr:
        """Convert a Python value back to the matching AST literal node."""
        if isinstance(value, bool):
            return BoolLiteral(1 if value else 0)
        if isinstance(value, int):
            return IntLiteral(value)
        if isinstance(value, float):
            return FloatLiteral(value)
        if isinstance(value, str):
            return StringLiteral(value)
        return value  # already an AST node

    # ------------------------------------------------------------------
    # Range checking
    # ------------------------------------------------------------------

    def _check_int_range(self, value: int, type_name: str, span) -> bool:
        """Emit an error if value is out of range for type_name. Returns True on error."""
        lo, hi = _INT_RANGES.get(type_name, (0, 0))
        magnitude = {"int32": "~2.14 billion", "int64": "~9.22 quintillion"}.get(type_name, "")

        if value > hi:
            self._diag.emit(ErrorCode.E5004, {"type_int": type_name, "magnitud": magnitude},
                [span], [(span, "value is too large for type `{type_int}`")])
            return True

        if value < lo:
            neg_magnitude = {"int32": "~ -2.14 billion", "int64": "~ -9.22 quintillion"}.get(type_name, "")
            self._diag.emit(ErrorCode.E5005, {"type_int": type_name, "magnitud": neg_magnitude},
                [span], [(span, "value is too small for type `{type_int}`")])
            return True

        return False

    def _check_float_range(self, value: float, type_name: str, span) -> bool:
        """Emit an error or warning if value is out of range for type_name.
        Returns True on error, False on underflow warning (which is non-fatal).
        """
        fmt     = "f" if type_name == "float" else "d"
        max_str = "3.40e38" if type_name == "float" else "1.79e308"

        try:
            packed   = struct.pack(fmt, value)
            repacked = struct.unpack(fmt, packed)[0]
        except (OverflowError, ValueError):
            return True

        if math.isinf(repacked) and not math.isinf(value):
            sign = "inf" if repacked > 0 else "-inf"
            self._diag.emit(ErrorCode.E5005,
                {"target_type": type_name, "max_val": max_str, "inf": sign},
                [span], [(span, f"value exceeds {type_name} range")])
            return True

        if repacked == 0.0 and value != 0.0:
            min_str = "1.18e-38" if type_name == "float" else "2.23e-308"
            self._diag.emit(ErrorCode.W5001,
                {"target_type": type_name, "min_val": min_str},
                [span], [(span, f"value underflows {type_name} minimum")])
            return False

        return False
    
    # ------------------------------------------------------------------
    # Index checking
    # ------------------------------------------------------------------
    def _check_index(self, idx: int, size: int, span_idx):
        if idx >= size:
            self._diag.emit(
                ErrorCode.E5007, {"index": idx, "size": size, "max_index": size-1}, [span_idx],
                [(span_idx, "It is out of bounds.")]
            )

        elif idx < 0:
            self._diag.emit(
                ErrorCode.E5008, {"index": idx}, [span_idx], [(span_idx, "it is negative.")]
            )