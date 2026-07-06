"""Type inference mixin for the Semantic analyzer.

This mixin is never instantiated directly — it is inherited by Semantic
so that _infer and its helpers have full access to self._diag,
self._struct_types, self._file_map, and self._check_call.
"""

from zonc.zonast import *
from zonc.zonc_errors import ErrorCode
from zonc.enviroment import Environment
from zonc.location_file import Span
from .semantic_types import leven_hint, err_span
import copy


class TypeInferenceMixin:

    # ------------------------------------------------------------------
    # Type compatibility
    # ------------------------------------------------------------------

    def _types_compatible(self, expected: int, found: int) -> bool:
        """Return True if found is assignable to expected.
        int64/int32 are interchangeable, as are float/double.
        """
        int_family   = {1, 6}
        float_family = {2, 7}
        return (
            expected == found
            or (expected in int_family   and found in int_family)
            or (expected in float_family and found in float_family)
        )

    # ------------------------------------------------------------------
    # Operand checking
    # ------------------------------------------------------------------

    def _check_operands(
        self,
        operands: tuple,
        return_type: ZonType,
        must_match: bool,
        operator: str,
        *valid_types: ZonType,
    ) -> ZonType:
        """Verify each operand is one of valid_types. If must_match, also
        verify both operands have the same type. Returns return_type on
        success, _ERROR_TYPE on failure.
        """
        n_valid = len(valid_types)

        for op_type, op_span in operands:
            if all(op_type.num != vt.num for vt in valid_types):
                valid_str = ", ".join(vt.name for vt in valid_types[:-1])
                valid_str += f" or {valid_types[-1].name}" if n_valid > 1 else valid_types[0].name
                self._diag.emit(
                    ErrorCode.E3003,
                    {"operator": operator, "valid_types": valid_str, "found_type": op_type.name},
                    [op_span],
                    [(op_span, "this operand is `{found_type}`, but `{operator}` expects {valid_types}")],
                )
                return self._ERROR_TYPE

        if must_match and operands[0][0].num != operands[1][0].num:
            left_num, right_num = operands[0][0].num, operands[1][0].num
            if left_num in {1, 6} and right_num in {1, 6}:
                return ZonType(1, "int64")
            if left_num in {2, 7} and right_num in {2, 7}:
                return ZonType(7, "double")
            self._diag.emit(
                ErrorCode.E3004,
                {"operator": operator,
                 "right_type": operands[1][0].name,
                 "left_type": operands[0][0].name},
                [operands[1][1]],
                [(operands[1][1],
                  "this is `{right_type}`, but `{operator}` expects `{left_type}` to match the left operand")],
            )
            return self._ERROR_TYPE

        return return_type

    # ------------------------------------------------------------------
    # Main inference entry point
    # ------------------------------------------------------------------

    def _infer(
        self,
        expr: NodeExpr,
        scope: Environment,
        is_field: bool = False,
        name: str | None = None,
    ) -> ZonType | tuple[ZonType, Environment]:
        """Infer and return the type of expr. Returns a (ZonType, Environment)
        tuple when the expression produces a struct instance.
        """
        e = self._ERROR_TYPE

        # -- literals --
        if isinstance(expr, IntLiteral):    return ZonType(1, "int64")
        if isinstance(expr, FloatLiteral):  return ZonType(7, "double")
        if isinstance(expr, BoolLiteral):   return ZonType(3, "bool")
        if isinstance(expr, StringLiteral): return ZonType(4, "string")

        # -- cast --
        if isinstance(expr, CastExpr):
            val_type = self._infer(expr.value, scope, name=name)
            if val_type.num == 0:
                return e
            if expr.zontype.num == 1:
                return self._check_operands(
                    ((val_type, expr.value.span),), ZonType(1, "int64"), False, "int64()",
                    ZonType(1, "int64"), ZonType(3, "bool"), ZonType(7, "double"),
                )
            if expr.zontype.num == 3:
                return self._check_operands(
                    ((val_type, expr.value.span),), ZonType(3, "bool"), False, "bool()",
                    ZonType(1, "int64"), ZonType(3, "bool"),
                )

        # -- binary --
        if isinstance(expr, BinaryExpr):
            op    = expr.operator
            left  = self._infer(expr.left,  scope, name=name)
            right = self._infer(expr.right, scope, name=name)
            if isinstance(left,  tuple): left  = left[0]
            if isinstance(right, tuple): right = right[0]
            if left.num == 0 or right.num == 0:
                return e

            ops = (left, expr.left.span), (right, expr.right.span)
            arith = {Operator.ADD:'+', Operator.SUB:'-', Operator.MUL:'*',
                     Operator.DIV:'/', Operator.MOD:'%', Operator.POW:"**"}

            if op in arith:
                return self._check_operands(ops, left, True, arith[op],
                    ZonType(1,"int64"), ZonType(2,"float"), ZonType(6,"int32"), ZonType(7,"double"))

            if op in (Operator.LT, Operator.GT, Operator.LE, Operator.GE):
                s = {Operator.LT:'<', Operator.GT:'>', Operator.LE:'<=', Operator.GE:'>='}[op]
                return self._check_operands(ops, ZonType(3,"bool"), True, s,
                    ZonType(1,"int64"), ZonType(2,"float"), ZonType(6,"int32"), ZonType(7,"double"))

            if op in (Operator.AND, Operator.OR):
                s = {Operator.AND:'and/&&', Operator.OR:'or/||'}[op]
                return self._check_operands(ops, left, False, s, ZonType(3,"bool"))

            if op in (Operator.EQ, Operator.NE):
                s = {Operator.EQ:'==', Operator.NE:'!='}[op]
                return self._check_operands(ops, ZonType(3,"bool"), True, s,
                    ZonType(1,"int64"), ZonType(2,"float"), ZonType(3,"bool"),
                    ZonType(6,"int32"), ZonType(7,"double"))

            if op in (Operator.BAND, Operator.BXOR, Operator.BOR, Operator.SL, Operator.SR,
                      Operator.BNAND, Operator.BNOR, Operator.BXNOR):
                names = {Operator.BAND:'band/&', Operator.BXOR:'bxor/^', Operator.BOR:'bor/|',
                         Operator.SL:'<<', Operator.SR:'>>', Operator.BNAND:'bnand/~&',
                         Operator.BNOR:'bnor/~|', Operator.BXNOR:'bxnor/~^'}
                return self._check_operands(ops, left, False, names[op],
                    ZonType(1,"int64"), ZonType(6,"int32"))

            if op in (Operator.CONCAT, Operator.EQ_STR, Operator.NE_STR):
                s = {Operator.CONCAT:'++', Operator.EQ_STR:'===', Operator.NE_STR:'!=='}[op]
                return self._check_operands(ops, left, False, s, ZonType(4,"string"))

        # -- unary --
        if isinstance(expr, UnaryExpr):
            op  = expr.operator
            val = self._infer(expr.value, scope, name=name)
            if isinstance(val, tuple): val = val[0]
            if val.num == 0: return e

            if op == Operator.NEG:
                return self._check_operands(((val, expr.value.span),), val, False, '-',
                    ZonType(1,"int64"), ZonType(2,"float"), ZonType(6,"int32"), ZonType(7,"double"))
            if op == Operator.BNOT:
                return self._check_operands(((val, expr.value.span),), val, False, 'bnot/~',
                    ZonType(1,"int64"), ZonType(6,"int32"))
            return self._check_operands(((val, expr.value.span),), val, False, 'not/!',
                ZonType(3,"bool"))

        # -- variable --
        if isinstance(expr, VariableExpr):
            symbol = scope.get(expr.name)
            if symbol is None:
                hint = leven_hint(expr.name, scope.collect("var"))
                self._diag.emit(ErrorCode.E3001, {"name": expr.name}, [expr.span],
                    [(expr.span, f"does not exist in this scope{hint}")])
                return e
            if symbol.is_empty:
                self._diag.emit(ErrorCode.E3002, {"name": expr.name}, [expr.span],
                    [(expr.span, "has no value at this point")])
                return e
            if symbol.scope_object is not None:
                return (symbol.zontype, copy.deepcopy(symbol.scope_object))
            return symbol.zontype

        # -- field access --
        if isinstance(expr, FieldExpr):
            return self._infer_field_expr(expr, scope)

        # -- struct construction --
        if isinstance(expr, ConstructExpr):
            return self._infer_construct_expr(expr, scope, name)

        # -- block expression --
        if isinstance(expr, BlockExpr):
            if is_field:
                span = err_span(expr.span, self._file_map)
                self._diag.emit(ErrorCode.E3028, None, [span],
                    [(span, "this expression is not allowed as a field default value")])
                return e
            self._check_stmts(expr.stmts, expr.scope, span_block=expr.span, is_expr=True)
            return self._infer(expr.stmts[expr.give_address].value, expr.scope, name=name)

        # -- if as expression --
        if isinstance(expr, IfForm):
            if is_field:
                span = err_span(expr.span, self._file_map)
                self._diag.emit(ErrorCode.E3028, None, [span],
                    [(span, "this expression is not allowed as a field default value")])
                return e
            if expr.else_branch is None:
                last = expr.elif_branches[-1].span if expr.elif_branches else expr.if_branch.span
                self._diag.emit(ErrorCode.E3010, None, [last],
                    [(err_span(last, self._file_map),
                      "an `else` branch is required when the if form is used as an expression")])
                return e
            give_values = self._check_if_form(expr, scope, is_expr=True)
            type_first  = give_values[0][0]
            mismatches  = [
                (span, f"this `give` returns `{t.name}`, but the if form expects `{type_first.name}`")
                for t, span in give_values[1:] if t.num != type_first.num
            ]
            if mismatches:
                self._diag.emit(ErrorCode.E3011, None, [s for _, s in mismatches], mismatches)
                return e
            return type_first

        # -- call as expression --
        if isinstance(expr, CallFunc):
            if is_field:
                span = err_span(expr.span, self._file_map)
                self._diag.emit(ErrorCode.E3028, None, [span],
                    [(span, "this expression is not allowed as a field default value")])
                return e
            self._check_call(expr, scope)
            func = scope.get(expr.name)
            if func is None:
                return e
            if func.return_type == ZonType(5, "void"):
                self._diag.emit(ErrorCode.E3026, {"name": expr.name}, [expr.span_name],
                    [(expr.span_name, "this call returns `void`")])
                return e
            return func.return_type

        return e

    # ------------------------------------------------------------------
    # Field expression inference
    # ------------------------------------------------------------------

    def _infer_field_expr(self, expr: FieldExpr, scope: Environment) -> ZonType:
        """Walk a chain of field accesses and return the final field's type."""
        path = []
        current = expr
        while isinstance(current, FieldExpr):
            path.insert(0, current)
            current = current.object_name

        root = scope.get(current.name)
        if root is None:
            hint = leven_hint(current.name, scope.collect("varob"))
            self._diag.emit(ErrorCode.E3030, {"name": current.name, "leven": hint}, [current.span],
                [(current.span, "`{name}` does not exist in this scope{leven}")])
            return self._ERROR_TYPE

        struct_entry = self._struct_types.get(root.zontype.name)
        if struct_entry is None:
            self._diag.emit(ErrorCode.E3031, {"name": current.name}, [current.span],
                [(current.span, "`{name}` is not a struct object")])
            return self._ERROR_TYPE

        obj_scope = struct_entry[1]
        for i, obj in enumerate(path):
            if i == len(path) - 1:
                break
            if not obj_scope.exists_here(obj.field):
                hint = leven_hint(obj.field, obj_scope.collect("var", is_field=True))
                self._diag.emit(ErrorCode.E3032,
                    {"struct_name": root.zontype.name, "field": obj.field}, [obj.span],
                    [(obj.span, "`{field}` does not exist in `{struct_name}`{leven}")])
                return self._ERROR_TYPE

            next_entry = self._struct_types.get(obj_scope.get(obj.field).zontype.name)
            if next_entry is None:
                self._diag.emit(ErrorCode.E3031, {"name": obj.field}, [obj.span],
                    [(obj.span, "`{name}` is not a struct object")])
                return self._ERROR_TYPE
            obj_scope = next_entry[1]

        final = path[-1].field
        if not obj_scope.exists_here(final):
            hint = leven_hint(final, obj_scope.collect("var", is_field=True))
            self._diag.emit(ErrorCode.E3040, {"field": final, "leven": hint}, [path[-1].span],
                [(path[-1].span, "`{field}` does not exist here{leven}")])
            return self._ERROR_TYPE

        field_sym = obj_scope.get(final)
        if field_sym.scope_object is not None:
            return (field_sym.zontype, field_sym.scope_object)
        return field_sym.zontype

    # ------------------------------------------------------------------
    # Construct expression inference
    # ------------------------------------------------------------------

    def _infer_construct_expr(
        self,
        expr: ConstructExpr,
        scope: Environment,
        name: str | None,
    ) -> ZonType:
        """Type-check a struct construction expression and return its type."""
        blueprint = self._struct_types.get(expr.name_struct)

        if blueprint is None:
            hint = leven_hint(expr.name_struct, list(self._struct_types))
            span = Span(expr.span.start, expr.span.start + 1, self._file_map)
            self._diag.emit(ErrorCode.E3038, {"name": expr.name_struct, "leven": hint}, [span],
                [(span, "`{name}` is not a declared struct{leven}")])
            return self._ERROR_TYPE

        n_list = 0 if expr.list_assign is None else len(expr.list_assign)
        n_dict = 0 if expr.dict_assign is None else len(expr.dict_assign)

        if len(blueprint[1]._symbols) < n_list + n_dict:
            span = Span(expr.span.start, expr.span.start + 1, self._file_map)
            self._diag.emit(
                ErrorCode.E3037,
                {"struct_name": expr.name_struct, "max": len(blueprint), "found": n_list + n_dict},
                [span], [(span, "too many values for `{struct_name}`")],
            )
            return self._ERROR_TYPE

        working_scope = Environment()
        working_scope._symbols = copy.deepcopy(blueprint[1]._symbols)

        field_status: dict[str, list] = {}
        field_list: list[tuple] = []
        for key, sym in working_scope._symbols.items():
            field_status[key] = [False, 0, not sym.is_empty]
            field_list.append((key, sym))

        if expr.list_assign is not None:
            for i, field_expr in enumerate(expr.list_assign):
                inferred = self._infer(field_expr, scope, name=name)
                if isinstance(inferred, tuple):
                    field_list[i][1].scope_object = inferred[1]
                    inferred = inferred[0]

                fname, fsym = field_list[i]
                if not fsym.mutability and not fsym.is_empty:
                    self._diag.emit(ErrorCode.E3034, {"field": fname},
                        [field_expr.span, fsym.decl_span],
                        [(field_expr.span, "`{field}` is immutable and cannot be reassigned"),
                         (fsym.decl_span, "here it was declared as `inmut`")])
                    continue

                if fsym.zontype.num == 0:
                    fsym.zontype = inferred
                elif inferred.num != fsym.zontype.num:
                    self._diag.emit(ErrorCode.E3029,
                        {"field": fname, "expected": fsym.zontype.name, "found": inferred.name},
                        [field_expr.span],
                        [(field_expr.span,
                          "this expression returns `{found}`, but `{field}` expects `{expected}`")])
                    continue

                field_status[fname][0] = True
                field_status[fname][1] = i
                fsym.is_empty = False

        if expr.dict_assign is not None:
            for key, (val_expr, val_span, key_span) in expr.dict_assign.items():
                inferred = self._infer(val_expr, scope)
                matched  = next(((fn, fs) for fn, fs in field_list if fn == key), None)

                if isinstance(inferred, tuple):
                    if matched:
                        matched[1].scope_object = inferred[1]
                    inferred = inferred[0]

                if matched is None:
                    hint = leven_hint(key, [fn for fn, _ in field_list])
                    self._diag.emit(ErrorCode.E3036,
                        {"field": key, "struct_name": expr.struct_type.name, "leven": hint},
                        [key_span], [(key_span, "`{field}` does not exist in `{struct_name}`{leven}")])
                    continue

                fname, fsym = matched
                if field_status[fname][0]:
                    self._diag.emit(ErrorCode.E3035, {"field": key}, [key_span],
                        [(key_span, "`{field}` was already assigned in this construct")])
                    continue

                if not fsym.mutability and not fsym.is_empty:
                    self._diag.emit(ErrorCode.E3034, {"field": fname},
                        [val_span, fsym.decl_span],
                        [(val_span, "`{field}` is immutable and cannot be reassigned"),
                         (fsym.decl_span, "here it was declared as `inmut`")])
                    continue

                if fsym.zontype.num == 0:
                    fsym.zontype = inferred
                elif inferred.num != fsym.zontype.num:
                    self._diag.emit(ErrorCode.E3029,
                        {"field": fname, "expected": fsym.zontype.name, "found": inferred.name},
                        [val_span],
                        [(val_span,
                          "this expression returns `{found}`, but `{field}` expects `{expected}`")])
                    continue

                field_status[fname][0] = True
                fsym.is_empty = False

        return (self._struct_types[expr.name_struct][0], working_scope)