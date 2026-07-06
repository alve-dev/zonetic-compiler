"""Semantic analyzer for Zonetic.

Entry point: Semantic.analyze(ast)

The class inherits TypeInferenceMixin so that _infer and its helpers
live in a separate file without losing access to shared state
(self._diag, self._struct_types, self._file_map, etc.).
"""

from zonc.zonast import *
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from zonc.enviroment import Environment, Symbol, FuncSymbol
from zonc.location_file import Span, FileMap
from .semantic_types import BranchTracker, FlowResult, leven_hint, err_span
from .type_inference import TypeInferenceMixin


class Semantic(TypeInferenceMixin):
    """Single-pass semantic analyzer for Zonetic.

    Responsibilities:
      - Register built-in functions and user-defined functions/structs (pre-scan).
      - Type-check every expression via _infer() (from TypeInferenceMixin).
      - Check control flow: return paths, break/continue placement, dead code.
      - Validate struct definitions and construct expressions.
    """

    # Maps struct name -> (ZonType, Environment with field symbols).
    # Populated during pre-scan when struct bodies are analyzed.
    _struct_types: dict[str, tuple] = {}

    _ERROR_TYPE = ZonType(0, "UNKNOWN")

    def __init__(self, diag: DiagnosticEngine, file_map: FileMap) -> None:
        self._diag = diag
        self._file_map = file_map
        self._current_func: FuncSymbol | None = None
        self._loop_depth: int = 0
        self.has_main = False

    # ------------------------------------------------------------------
    # Built-in registration
    # ------------------------------------------------------------------

    def _register_builtins(self, scope: Environment) -> None:
        """Define all native functions in the global scope."""
        s = Span(0, 0, self._file_map)

        def _native(params, return_type, variadic=False):
            return FuncSymbol(params, s, s, return_type, is_native=True, is_varidic=variadic)

        def _param(name, type_num, type_name, default=None):
            return Param(False, name, ZonType(type_num, type_name), default, s, s)

        scope.define("print",      _native([], ZonType(5, "void"), variadic=True))
        scope.define("println",    _native([], ZonType(5, "void"), variadic=True))
        scope.define("readInt",    _native([_param("prompt", 4, "string", StringLiteral(" ", s))], ZonType(1, "int")))
        scope.define("readFloat",  _native([_param("prompt", 4, "string", StringLiteral(" ", s))], ZonType(2, "float")))
        scope.define("readString", _native([_param("prompt", 4, "string", StringLiteral(" ", s))], ZonType(4, "string")))
        scope.define("alloc",      _native([_param("size",  1, "int64")], ZonType(1, "int64")))
        scope.define("store",      _native([_param("ptr",   1, "int64"), _param("value", 1, "int64")], ZonType(5, "void")))
        scope.define("load",       _native([_param("ptr",   1, "int64")], ZonType(1, "int64")))
        scope.define("len",        _native([_param("s",     4, "string")], ZonType(4, "string")))

        # TODO: remove alloc/store/load once real heap support lands

    # ------------------------------------------------------------------
    # Pre-scan
    # ------------------------------------------------------------------

    def _pre_scan(self, ast: Program, scope: Environment) -> None:
        """Register all top-level functions and structs before checking bodies."""
        self._register_builtins(scope)
        struct_name_spans: dict[str, Span] = {}

        for node in ast.stmts:
            if isinstance(node, FuncForm):
                existing = scope.get(node.name)
                if existing is not None:
                    kind = "builtin-function" if existing.is_native else "function"
                    spans  = [node.span_name] if existing.is_native else [node.span_name, existing.name_span]
                    labels = [(node.span_name, "this name is already in use")]
                    if not existing.is_native:
                        labels.append((existing.name_span, "first defined as a function here"))
                    self._diag.emit(ErrorCode.E3013, {"name": node.name, "kind": kind}, spans, labels)
                    continue

                if node.name in self._struct_types:
                    self._diag.emit(
                        ErrorCode.E3041, {"name": node.name},
                        [node.span_name, struct_name_spans[node.name]],
                        [(node.span_name, "`{name}` is already in use as a struct name"),
                         (struct_name_spans[node.name], "the name was taken by this struct")],
                    )
                    continue

                scope.define(node.name, FuncSymbol(node.params, node.span, node.span_name, node.return_type))

            elif isinstance(node, StructForm):
                existing_func = scope.get(node.name)
                if existing_func is not None:
                    self._diag.emit(
                        ErrorCode.E3042, {"name": node.name},
                        [node.span, existing_func.name_span],
                        [(err_span(node.span, self._file_map), "`{name}` is already in use as a function name"),
                         (existing_func.name_span, "the name was taken from this function")],
                    )
                    continue

                self._struct_types[node.name] = None
                struct_name_spans[node.name] = node.span_name

        for node in ast.stmts:
            if isinstance(node, StructForm):
                self._check_struct_form(node)

    # ------------------------------------------------------------------
    # Top-level entry point
    # ------------------------------------------------------------------

    def analyze(self, ast: Program, is_expr: bool = False) -> None:
        """Run the full semantic analysis on the AST."""
        scope = ast.scope
        self._pre_scan(ast, scope)
        self.has_main = scope.exists("main")

        if self.has_main:
            self._check_top_level_stmts(ast.stmts, scope)

        self._check_stmts(ast.stmts, scope, is_expr=is_expr)

    def _check_top_level_stmts(self, stmts: list[Node], scope: Environment) -> None:
        """Reject statements only valid inside functions when at top level."""
        for stmt in stmts:
            if isinstance(stmt, DeclarationStmt):
                self._diag.emit(ErrorCode.E3035, None, [stmt.span],
                    [(stmt.span_name, "global variables must be initialized at declaration.")])

            elif isinstance(stmt, AssignmentStmt):
                self._diag.emit(ErrorCode.E3039, None, [stmt.span],
                    [(stmt.span_name, "assignments are only permitted inside functions in structured mode.")])
                self._check_no_block_in_expr(stmt.value)

            elif isinstance(stmt, IfForm):
                self._diag.emit(ErrorCode.E3047, None, [stmt.span],
                    [(err_span(stmt.span, self._file_map), "control flow statements cannot appear at top level.")])

            elif isinstance(stmt, WhileForm):
                self._diag.emit(ErrorCode.E3048, None, [stmt.span],
                    [(err_span(stmt.span, self._file_map), "loops are only valid inside functions.")])

            elif isinstance(stmt, CallFunc):
                self._diag.emit(ErrorCode.E3049, None, [stmt.span],
                    [(stmt.span_name, "function calls are only allowed inside other functions.")])

            elif isinstance(stmt, BlockExpr):
                self._diag.emit(ErrorCode.E3050, None, [stmt.span],
                    [(err_span(stmt.span, self._file_map), "stray block found at top level.")])

            elif isinstance(stmt, InitializationStmt):
                self._check_no_block_in_expr(stmt.assign_stmt.value)

    def _check_no_block_in_expr(self, expr: NodeExpr) -> None:
        if isinstance(expr, BlockExpr):
            self._diag.emit(ErrorCode.E3051, None, [expr.span],
                [(err_span(expr.span, self._file_map), "blocks cannot be used as expressions here.")])
        elif isinstance(expr, BinaryExpr):
            self._check_no_block_in_expr(expr.left)
            self._check_no_block_in_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._check_no_block_in_expr(expr.value)

    # ------------------------------------------------------------------
    # Statement checking
    # ------------------------------------------------------------------

    def _check_stmts(
        self,
        stmts: list[Node],
        scope: Environment,
        span_block: Span = None,
        is_expr: bool = False,
        is_func_body: bool = False,
        branch_tracker: BranchTracker = None,
    ) -> FlowResult:
        flow = FlowResult()

        if not stmts:
            self._diag.emit(ErrorCode.E3043, None, [span_block],
                [(err_span(span_block, self._file_map), "this block is empty")])
            return flow

        for i, stmt in enumerate(stmts):

            if isinstance(stmt, DeclarationStmt):
                self._check_declaration(stmt, scope)

            elif isinstance(stmt, AssignmentStmt):
                self._check_assignment_in_stmts(stmt, scope, branch_tracker)

            elif isinstance(stmt, InitializationStmt):
                self._check_initialization(stmt, scope)

            elif isinstance(stmt, BlockExpr):
                block_flow = self._check_stmts(stmt.stmts, stmt.scope, span_block=stmt.span)
                if block_flow.has_returned:
                    flow.has_returned = True
                    flow.possible_not_return.extend(block_flow.possible_not_return)

            elif isinstance(stmt, GiveStmt):
                if is_func_body:
                    self._diag.emit(ErrorCode.E3018, None, [stmt.span],
                        [(stmt.span, "`give` is only for block expressions, not function bodies")])
                else:
                    flow.has_given = True
                    flow.give_type = self._infer(stmt.value, scope)
                    if isinstance(flow.give_type, tuple):
                        flow.give_type = flow.give_type[0]
                    flow.give_span = stmt.span

            elif isinstance(stmt, IfForm):
                if_flow = self._check_if_form(stmt, scope, is_expr=False)
                if if_flow.has_returned:
                    flow.has_returned = True
                    flow.possible_not_return.extend(if_flow.possible_not_return)

            elif isinstance(stmt, WhileForm):
                self._loop_depth += 1
                while_flow = self._check_while_form(stmt, scope)
                self._loop_depth -= 1
                if while_flow.has_returned:
                    flow.possible_not_return.extend(while_flow.possible_not_return)

            elif isinstance(stmt, (BreakStmt, ContinueStmt)):
                keyword = "break" if isinstance(stmt, BreakStmt) else "continue"
                if self._loop_depth == 0:
                    self._diag.emit(ErrorCode.E3012, {"keyword": keyword}, [stmt.span],
                        [(stmt.span, "can only be used in loops")])
                elif isinstance(stmt, BreakStmt):
                    flow.has_broken = True
                else:
                    flow.has_continued = True

            elif isinstance(stmt, FuncForm):
                if is_func_body:
                    self._diag.emit(ErrorCode.E3017, {"inner_name": stmt.name}, [stmt.span_name],
                        [(stmt.span_name, "nested functions are forbidden")])
                else:
                    self._check_func_form(stmt, scope)

            elif isinstance(stmt, ReturnStmt):
                if is_func_body:
                    flow.has_global_returned = True
                flow.has_returned = True
                flow.return_type  = self._check_return(stmt, scope)

            elif isinstance(stmt, CallFunc):
                self._check_call(stmt, scope)

            elif isinstance(stmt, AssignmentFieldStmt):
                self._check_field_assignment(stmt, scope)

            if any([flow.has_returned, flow.has_given, flow.has_broken, flow.has_continued]):
                if i < len(stmts) - 1:
                    self._warn_dead_code(stmt, stmts, is_func_body)
                    break

        return flow

    def _check_assignment_in_stmts(
        self,
        stmt: AssignmentStmt,
        scope: Environment,
        branch_tracker: BranchTracker,
    ) -> None:
        symbol = scope.get(stmt.name)
        if isinstance(symbol, FuncSymbol):
            return
        if symbol is None:
            hint = leven_hint(stmt.name, scope.collect("var"))
            self._diag.emit(ErrorCode.E3001, {"name": stmt.name, "leven": hint}, [stmt.span],
                [(stmt.span_name, "does not exist in this scope{leven}")])
            return

        was_empty = symbol.is_empty
        self._check_assignment(stmt, scope, not_empty=True)

        if branch_tracker is not None and not scope.exists_here(stmt.name):
            if stmt.name in branch_tracker.counts:
                branch_tracker.counts[stmt.name][0] += 1
            elif symbol is not None and was_empty:
                branch_tracker.counts[stmt.name] = [1, symbol.decl_span]
                symbol.is_empty = True

    def _check_initialization(self, stmt: InitializationStmt, scope: Environment) -> None:
        inferred = self._infer(stmt.assign_stmt.value, scope, name=stmt.assign_stmt.name)
        struct_scope = None
        if isinstance(inferred, tuple):
            struct_scope, inferred = inferred[1], inferred[0]

        self._check_declaration(stmt.decl_stmt, scope)
        if inferred.num == 0:
            return

        symbol = scope.get(stmt.decl_stmt.name)
        if symbol.zontype.num == 0:
            symbol.zontype.name = inferred.name
            symbol.zontype.num  = inferred.num
        elif not self._types_compatible(symbol.zontype.num, inferred.num):
            err = (
                stmt.assign_stmt.value.stmts[stmt.assign_stmt.value.give_address].value.span
                if isinstance(stmt.assign_stmt.value, BlockExpr)
                else stmt.assign_stmt.value.span
            )
            self._diag.emit(
                ErrorCode.E3006,
                {"name": stmt.assign_stmt.name,
                 "expected_type": symbol.zontype.name,
                 "found_type": inferred.name},
                [stmt.assign_stmt.span],
                [(err, "this expression returns `{found_type}`, but `{name}` expects `{expected_type}`")],
            )
            return

        symbol.is_empty = False
        if struct_scope is not None:
            symbol.scope_object = struct_scope

    def _warn_dead_code(self, stmt: Node, stmts: list[Node], is_func_body: bool) -> None:
        last = stmts[-1]
        if isinstance(stmt, GiveStmt):
            self._diag.emit(ErrorCode.W3001, None, [stmt.span, last.span],
                [(stmt.span, "this `give` exits the current block expr"),
                 (last.span, "...so this code will never be executed.")])
        elif isinstance(stmt, ReturnStmt) and is_func_body:
            self._diag.emit(ErrorCode.W3005, {"aux": "}"}, [stmt.span, last.span],
                [(stmt.span, "this `return` exits the current function"),
                 (last.span, "...so this code will never be executed.")])
        elif isinstance(stmt, (BreakStmt, ContinueStmt)):
            keyword = "break" if isinstance(stmt, BreakStmt) else "continue"
            self._diag.emit(ErrorCode.W3006, {"keyword": keyword}, [stmt.span, last.span],
                [(stmt.span, "this `{keyword}` exits the current loop"),
                 (last.span, "...so this code will never be executed.")])

    # ------------------------------------------------------------------
    # Declaration and assignment
    # ------------------------------------------------------------------

    def _check_declaration(self, node: DeclarationStmt, scope: Environment, is_param: bool = False) -> None:
        existing = scope.get(node.name)
        if existing is not None and isinstance(existing, FuncSymbol):
            self._diag.emit(ErrorCode.E3013, {"name": node.name, "kind": "variable"},
                [node.span_name, existing.name_span],
                [(node.span_name, "this name is already in use"),
                 (existing.name_span, "first defined as a function here")])
            return
        scope.define(node.name, Symbol(node.mut, node.type, not is_param, node.span))

    def _check_assignment(
        self,
        node: AssignmentStmt,
        scope: Environment,
        not_empty: bool,
        is_param: bool = False,
        is_field: bool = False,
        field_scope: Environment = None,
    ) -> None:
        symbol = field_scope.get(node.name) if field_scope is not None else scope.get(node.name)

        if symbol is None:
            hint = leven_hint(node.name, scope.collect("var"))
            self._diag.emit(ErrorCode.E3001, {"name": node.name}, [node.span],
                [(node.span_name, f"does not exist in this scope{hint}")])
            return

        if isinstance(symbol, FuncSymbol):
            return

        if not symbol.mutability and not symbol.is_empty:
            self._diag.emit(ErrorCode.E3005, {"name": node.name}, [node.span, symbol.decl_span],
                [(node.span_name, "is immutable, it was already assigned a value"),
                 (symbol.decl_span, "was first defined as immutable here")])
            return

        if self._loop_depth > 0 and not scope.exists_here(node.name) and not symbol.mutability and symbol.is_empty:
            self._diag.emit(ErrorCode.E3016, None, [node.span],
                [(node.span_name, "cannot initialize an outer `inmut` variable here")])
            return

        value_type = self._infer(node.value, scope, is_field, node.name)
        if isinstance(value_type, tuple):
            symbol.scope_object = value_type[1]
            value_type = value_type[0]

        if value_type.num == 0:
            return

        if symbol.zontype.num == 0:
            symbol.zontype.name = value_type.name
            symbol.zontype.num  = value_type.num
        elif not self._types_compatible(symbol.zontype.num, value_type.num):
            err = (
                node.value.stmts[node.value.give_address].value.span
                if isinstance(node.value, BlockExpr)
                else node.value.span
            )
            self._diag.emit(ErrorCode.E3006,
                {"name": node.name, "expected_type": symbol.zontype.name, "found_type": value_type.name},
                [node.span],
                [(err, "this expression returns `{found_type}`, but `{name}` expects `{expected_type}`")])
            return

        if symbol.is_empty and not_empty and not is_param:
            symbol.is_empty = False

    # ------------------------------------------------------------------
    # Struct form
    # ------------------------------------------------------------------

    def _check_struct_form(self, node: StructForm) -> None:
        for stmt in node.block_expr.stmts:
            if isinstance(stmt, DeclarationStmt):
                if node.block_expr.scope.exists_here(stmt.name):
                    existing = node.block_expr.scope.get(stmt.name)
                    self._diag.emit(ErrorCode.E3044, {"name": stmt.name},
                        [stmt.span_name, existing.decl_span],
                        [(stmt.span_name, "`{name}` is already declared as a field in this struct"),
                         (existing.decl_span, "the name was already taken by this declaration.")])
                    continue
                self._check_declaration(stmt, node.block_expr.scope)

            elif isinstance(stmt, AssignmentStmt):
                if not node.block_expr.scope.exists_here(stmt.name):
                    self._diag.emit(ErrorCode.E3045, {"name": stmt.name}, [stmt.span_name],
                        [(stmt.span_name, "`{name}` is not a field of this struct")])
                    continue
                self._check_assignment(stmt, node.block_expr.scope, not_empty=True, is_field=True)

            else:
                self._diag.emit(ErrorCode.E3046, None, [stmt.span],
                    [(err_span(stmt.span, self._file_map),
                      "only field declarations and assignments are allowed inside a struct")])

        self._struct_types[node.name] = (node.zontype, node.block_expr.scope)

    # ------------------------------------------------------------------
    # Function form
    # ------------------------------------------------------------------

    def _check_func_form(self, node: FuncForm, scope: Environment) -> None:
        prev_func = self._current_func
        self._current_func = scope.get(node.name)

        if node.params is not None:
            for param in node.params:
                if node.block_expr.scope.exists_here(param.name):
                    sym = node.block_expr.scope.get(param.name)
                    if isinstance(sym, Symbol):
                        self._diag.emit(ErrorCode.E3027, {"name": param.name},
                            [param.span, sym.decl_span],
                            [(param.span_name, "`{name}` is already declared as a parameter"),
                             (sym.decl_span, "`{name}` was declared here")])
                        continue

                decl = DeclarationStmt(param.name, param.mut, param.zontype, param.span_name, param.span)
                self._check_declaration(decl, node.block_expr.scope, is_param=(param.default is None))

                if param.default is not None:
                    assign = AssignmentStmt(param.name, param.default, param.span, param.span_name)
                    self._check_assignment(assign, node.block_expr.scope, not_empty=True, is_param=True)

        flow = self._check_stmts(
            node.block_expr.stmts, node.block_expr.scope,
            span_block=node.span, is_func_body=True,
        )

        if not flow.has_global_returned and flow.possible_not_return and node.return_type.num != 0:
            for missing in flow.possible_not_return:
                self._diag.emit(ErrorCode.E3019, {"func_name": node.name}, [missing["span"]],
                    [(err_span(missing["span"], self._file_map),
                      "missing `else` or a global `return` after this if form")])

        self._current_func = prev_func

    # ------------------------------------------------------------------
    # Return statement
    # ------------------------------------------------------------------

    def _check_return(self, node: ReturnStmt, scope: Environment) -> ZonType:
        if self._current_func is None:
            self._diag.emit(ErrorCode.E3014, None, [node.span],
                [(node.span, "this `return` is not inside a function scope")])
            return self._ERROR_TYPE

        ret_type = ZonType(5, "void") if node.value is None else self._infer(node.value, scope)
        if isinstance(ret_type, tuple):
            ret_type = ret_type[0]

        expected = self._current_func.return_type
        if ret_type.num != expected.num and not self._types_compatible(expected.num, ret_type.num):
            self._diag.emit(ErrorCode.E3015,
                {"func_name": self._current_func.name_span.to_string(),
                 "found": ret_type.name.lower(), "expected": expected.name},
                [node.span], [(node.span, "expected `{expected}`, found `{found}`")])
        return ret_type

    # ------------------------------------------------------------------
    # Call expression
    # ------------------------------------------------------------------

    def _check_call(self, node: CallFunc, scope: Environment) -> None:
        func = scope.get(node.name)

        if func is None or isinstance(func, Symbol):
            hint = leven_hint(node.name, scope.collect("fun"))
            self._diag.emit(ErrorCode.E3020, {"name": node.name, "leven": hint}, [node.span],
                [(node.span, "cannot call `{name}` because it has not been defined{leven}")])
            return

        if func.is_native and func.is_varidic:
            if node.params:
                for expr in node.params:
                    self._infer(expr, scope)
            return

        param_status: dict[str, list] = {}
        if func.params:
            for p in func.params:
                param_status[p.name] = [False, 0, p.default is not None]

        if node.params:
            if not param_status:
                self._diag.emit(ErrorCode.E3021, None, [node.span, func.name_span],
                    [(node.span, "these parameters are not expected here"),
                     (func.name_span, "this function is defined with no parameters")])
                return

            for i, param_expr in enumerate(node.params):
                inferred = self._infer(param_expr, scope)
                if isinstance(inferred, tuple): inferred = inferred[0]
                if inferred.num == 0: continue

                expected_param = func.params[i]
                if inferred.num != expected_param.zontype.num:
                    self._diag.emit(ErrorCode.E3022,
                        {"found": inferred.name, "expect": expected_param.zontype.name},
                        [param_expr.span],
                        [(param_expr.span, "this expression is `{found}` but the parameter expects `{expect}`")])
                    continue

                param_status[expected_param.name][0] = True
                param_status[expected_param.name][1] = i

        if node.keyparams:
            if not param_status:
                self._diag.emit(ErrorCode.E3021, None, [func.name_span, node.span],
                    [(func.name_span, "this function is defined with no parameters"),
                     (node.span, "these parameters are not expected here")])
                return

            for key, (val_expr, val_span, key_span) in node.keyparams.items():
                inferred = self._infer(val_expr, scope)
                if isinstance(inferred, tuple): inferred = inferred[0]
                if inferred.num == 0: return

                matched = next((p for p in func.params if p.name == key), None)
                if matched is None:
                    hint = leven_hint(key, list(param_status))
                    self._diag.emit(ErrorCode.E3023,
                        {"name": node.name, "name_param": key, "leven": hint},
                        [val_span], [(key_span, "this parameter does not exist in `{name}`{leven}")])
                    continue

                if param_status[matched.name][0]:
                    self._diag.emit(ErrorCode.E3024,
                        {"name_func": node.name, "name_param": key,
                         "param_pos": param_status[matched.name][1]},
                        [val_span], [(val_span, "this parameter already received a value")])
                    continue

                if inferred.num != matched.zontype.num:
                    self._diag.emit(ErrorCode.E3022,
                        {"found": inferred.name, "expect": matched.zontype.name},
                        [val_span],
                        [(val_span, "this expression is `{found}` but the parameter expects `{expect}`")])
                    continue

                param_status[matched.name][0] = True

        missing = sum(1 for v in param_status.values() if not v[0] and not v[2])
        if missing > 0:
            self._diag.emit(ErrorCode.E3025, {"name_func": node.name, "num": missing}, [node.span_name],
                [(node.span_name, "missing {num} required parameter(s)")])

    # ------------------------------------------------------------------
    # Field assignment
    # ------------------------------------------------------------------

    def _check_field_assignment(self, stmt: AssignmentFieldStmt, scope: Environment) -> None:
        path = []
        current = stmt.object_name
        while isinstance(current, FieldExpr):
            path.insert(0, current)
            current = current.object_name

        root = scope.get(current.name)
        if root is None:
            hint = leven_hint(current.name, scope.collect("varob"))
            self._diag.emit(ErrorCode.E3030, {"name": current.name, "leven": hint}, [current.span],
                [(current.span, "`{name}` does not exist in this scope{leven}")])
            return

        obj_scope = root.scope_object
        if obj_scope is None:
            self._diag.emit(ErrorCode.E3031, {"name": current.name}, [current.span],
                [(current.span, "`{name}` is not a struct object")])
            return

        for obj in path:
            if not obj_scope.exists_here(obj.field):
                hint = leven_hint(obj.field, obj_scope.collect("var", is_field=True))
                self._diag.emit(ErrorCode.E3032,
                    {"struct_name": root.zontype.name, "field": obj.field, "leven": hint},
                    [obj.span], [(obj.span, "`{field}` does not exist in `{struct_name}`{leven}")])
                return
            next_sym = obj_scope.get(obj.field)
            if next_sym is None or next_sym.scope_object is None:
                self._diag.emit(ErrorCode.E3031, {"name": obj.field}, [obj.span],
                    [(obj.span, "`{name}` is not a struct object")])
                return
            obj_scope = next_sym.scope_object

        if not obj_scope.exists_here(stmt.field_assign.name):
            hint = leven_hint(stmt.field_assign.name, obj_scope.collect("var", is_field=True))
            self._diag.emit(ErrorCode.E3033, {"field": stmt.field_assign.name, "leven": hint},
                [stmt.field_assign.span],
                [(stmt.field_assign.span_name,
                  "`{field}` is not a valid field for assignment here{leven}")])
            return

        self._check_assignment(stmt.field_assign, scope, not_empty=True, field_scope=obj_scope)

    # ------------------------------------------------------------------
    # Control flow forms
    # ------------------------------------------------------------------

    def _check_if_form(self, node: IfForm, scope: Environment, is_expr: bool) -> FlowResult | list:
        tracker     = BranchTracker()
        give_values = []
        flow        = FlowResult()

        def eval_branch(branch, check_cond: bool) -> FlowResult:
            if check_cond and isinstance(branch.cond, BoolLiteral):
                if branch.cond.value == 1 and (node.elif_branches or node.else_branch):
                    self._diag.emit(ErrorCode.W3002, None, [branch.cond.span],
                        [(branch.cond.span, "this condition is always `true`")])
                elif branch.cond.value == 0:
                    self._diag.emit(ErrorCode.W3003, None, [branch.cond.span],
                        [(branch.cond.span, "this condition is always `false`")])
            return self._check_if_branch(branch, scope, tracker, check_cond, is_expr)

        if_flow = eval_branch(node.if_branch, check_cond=True)
        if is_expr and if_flow.has_given:
            give_values.append((if_flow.give_type, if_flow.give_span))
        if if_flow.has_returned:
            flow.has_returned = True

        if node.else_branch is None:
            if flow.has_returned:
                flow.possible_not_return.append({"span": node.span})
            if tracker.counts:
                last_span = node.elif_branches[-1].span if node.elif_branches else node.if_branch.span
                self._diag.emit(ErrorCode.E3008, None, [last_span],
                    [(err_span(last_span, self._file_map), "an `else` branch was expected here")])
                return flow

        if node.elif_branches:
            for elif_node in node.elif_branches:
                elif_flow = eval_branch(elif_node, check_cond=True)
                if is_expr and elif_flow.has_given:
                    give_values.append((elif_flow.give_type, elif_flow.give_span))
                if elif_flow.has_returned and flow.has_returned and elif_flow.return_type != if_flow.return_type:
                    flow.possible_not_return.append({"span": node.span})

        if node.else_branch:
            else_flow = eval_branch(node.else_branch, check_cond=False)
            if is_expr and else_flow.has_given:
                give_values.append((else_flow.give_type, else_flow.give_span))

        for sym_name, (count, decl_span) in tracker.counts.items():
            if count < node.len_branch:
                self._diag.emit(ErrorCode.E3009, {"name": sym_name}, [node.span, decl_span],
                    [(err_span(node.span, self._file_map),
                      "`{name}` is first assigned inside this if form, but not in every branch"),
                     (decl_span,
                      "`{name}` is declared empty here and may still be empty after the if form")])
            else:
                scope.get(sym_name).is_empty = False

        return give_values if is_expr else flow

    def _check_if_branch(
        self,
        branch: IfBranch,
        scope: Environment,
        tracker: BranchTracker,
        check_cond: bool,
        is_expr: bool,
    ) -> FlowResult:
        if check_cond:
            cond_type = self._infer(branch.cond, scope)
            if isinstance(cond_type, tuple): cond_type = cond_type[0]
            if cond_type.num != 3:
                self._diag.emit(ErrorCode.E3007, {"found_type": cond_type.name},
                    [Span(branch.span.start, branch.cond.span.end, self._file_map)],
                    [(branch.cond.span,
                      "this expression returns `{found_type}`, but a condition expects `bool`")])

        return self._check_stmts(
            branch.block.stmts, branch.block.scope,
            span_block=branch.block.span, is_expr=is_expr,
            branch_tracker=tracker,
        )

    def _check_while_form(self, node: WhileForm, scope: Environment) -> FlowResult:
        cond_type = self._infer(node.condition_field, scope)
        if isinstance(cond_type, tuple): cond_type = cond_type[0]
        if cond_type.num != 3:
            self._diag.emit(ErrorCode.E3007, {"found_type": cond_type.name},
                [Span(node.span.start, node.condition_field.span.end, self._file_map)],
                [(node.condition_field.span,
                  "this expression returns `{found_type}`, but a condition expects `bool`")])

        flow = self._check_stmts(node.block_expr.stmts, node.block_expr.scope, node.block_expr.span)

        if isinstance(node.condition_field, BoolLiteral):
            if node.condition_field.value == 1 and not flow.has_broken:
                self._diag.emit(ErrorCode.W3004, None, [node.span],
                    [(err_span(node.span, self._file_map), "this loop has no exit point")])
            elif node.condition_field.value == 0:
                self._diag.emit(ErrorCode.W3003, None, [node.condition_field.span],
                    [(node.condition_field.span, "this condition is always `false`")])
        return flow