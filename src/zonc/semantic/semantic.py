from zonc.zonast import *
from zonc.zonc_errors import DiagnosticEngine
from zonc.enviroment import *
from zonc.zonc_errors import ErrorCode
from zonc.location_file import Span, FileMap
from dataclasses import dataclass, field
import copy

# TODO: hacxer error para printeo raros como object struct, 


@dataclass
class DictTemp:
    dict_temp: dict


@dataclass
class FlowResult:
    has_global_returned: bool = False
    has_returned: bool = False
    return_type: ZonType | None = None
    possible_not_return: list[dict] = field(default_factory=list)
    has_given: bool = False
    give_type: ZonType | None = None
    give_span: Span | None = None
    has_broken: bool = False
    has_continued: bool = False


class Semantic:
    def __init__(self, diag: DiagnosticEngine, file_map: FileMap) -> None:
        self.diag = diag
        self.file_map = file_map
        self.current_func: FuncSymbol | None = None
        self.loop_depth: int = 0
        
    def insert_std(self, scope: Enviroment):
        span_aux = Span(0, 0, self.file_map)
        scope.define("print", FuncSymbol([], span_aux, span_aux, ZonType(5, "void"), True, True))
        scope.define("readInt", FuncSymbol(
            [Param(False, "prompt", ZonType(4, "string"), StringLiteral(" ", span_aux), span_aux, span_aux)],
            span_aux, span_aux, ZonType(1, "int"), True, True))
        scope.define("readFloat", FuncSymbol(
            [Param(False, "prompt", ZonType(4, "string"), StringLiteral(" ", span_aux), span_aux, span_aux)],
            span_aux, span_aux, ZonType(2, "float"), True, True))
        scope.define("readString", FuncSymbol(
            [Param(False, "prompt", ZonType(4, "string"), StringLiteral(" ", span_aux), span_aux, span_aux)],
            span_aux, span_aux, ZonType(4, "string"), True, True))
          
    TYPE_TABLE = {}

    def pre_scan(self, ast: Node, scope: Enviroment):
        self.insert_std(scope)
        spans_structs = {}
        for node in ast.stmts:
            if isinstance(node, FuncForm):
                get: FuncSymbol = scope.get_symbol(node.name)
                if not(get is None):
                    if get.is_native:
                        self.diag.emit(
                            ErrorCode.E3013,
                            { "name" : node.name, "kind" : "builtin-function" },
                            [node.span_name],
                            [(node.span_name, "this name is already in use for a native function")]
                        )
                        continue
                    
                    self.diag.emit(
                        ErrorCode.E3013,
                        { "name" : node.name, "kind" : "function" },
                        [node.span_name, get.name_span],
                        [(node.span_name, "this name is already in use"), (get.name_span, "first defined as a function here")]
                    )
                    continue
                    
                elif node.name in self.TYPE_TABLE:
                    self.diag.emit(
                        ErrorCode.E3041, { "name" : node.name }, [node.span_name, spans_structs[node.name]],
                        [(node.span_name, "`{name}` is already in use as a struct name"), (spans_structs[node.name], "The name has already been taken by this struct")]
                    )
                    continue
                
                scope.define(
                    node.name,
                    FuncSymbol(node.params, node.span, node.span_name, node.return_type)
                )
                
            elif isinstance(node, StructForm):
                get_func = scope.get_symbol(node.name)
                if get_func is None:
                    self.TYPE_TABLE.update({node.name : None})
                    spans_structs.update({node.name : node.span_name})
                
                else:
                    self.diag.emit(
                        ErrorCode.E3042, { "name" : node.name }, [node.span, get_func.name_span],
                        [(Span(node.span.end-1, node.span.end, self.file_map), "`{name}` is already in use as a function name"), (get_func.name_span, "The name was taken from this function")]
                    )
                    continue
                
        for node in ast.stmts:
            if isinstance(node, StructForm):
                self.check_struct_form(node)

                    
    def check_ast(self, ast: Program, is_expr: bool) -> None | ZonType:
        scope: Enviroment = ast.scope
        self.pre_scan(ast, scope)
        self.evaluate_statements(ast.stmts, scope, is_expr=is_expr)
        return None

    def evaluate_statements(
        self,
        stmts: list[Node],
        scope: Enviroment,
        span_block: Span = None,
        is_expr: bool = False,
        is_func_body: bool = False,
        sym_empty_count: DictTemp = None,
    ) -> FlowResult:
        flow = FlowResult()
        len_stmts = len(stmts)
        
        if len_stmts < 1:
            self.diag.emit(
                ErrorCode.E3043, None, [span_block], [(Span(span_block.end-1, span_block.end, self.file_map), "this block is empty")]
            )
        
        for i, stmt in enumerate(stmts):
            if isinstance(stmt, DeclarationStmt):    
                self.check_declaration_stmt(stmt, scope)
                
            elif isinstance(stmt, AssignmentStmt):
                symbol = scope.get_symbol(stmt.name)
                
                if isinstance(symbol, FuncSymbol): continue
                if symbol is None:
                    self.diag.emit(ErrorCode.E3001, { "name" : stmt.name }, [stmt.span], [(stmt.span_name, "does not exist in this scope")])
                    continue
                    
                is_empty = symbol.is_empty
                self.check_assignment_stmt(stmt, scope, True)
                if not(sym_empty_count is None) and not(scope.exist_here(stmt.name)):
                    if stmt.name in sym_empty_count.dict_temp:
                        sym_empty_count.dict_temp[stmt.name][0] += 1
                    else:
                        if not scope.exist_here(stmt.name):
                            if not(symbol is None) and is_empty:
                                sym_empty_count.dict_temp.update({stmt.name : [1, symbol.decl_span]})
                    
                                symbol.is_empty = True
            
            elif isinstance(stmt, BlockExpr):
                block_flow = self.evaluate_statements(stmt.stmts, stmt.scope, span_block=stmt.span, is_expr=False)
                if block_flow.has_returned:
                    flow.has_returned = True
                    flow.possible_not_return.extend(block_flow.possible_not_return)
                
            elif isinstance(stmt, GiveStmt):
                if is_func_body:
                    self.diag.emit(
                        ErrorCode.E3018, None, [stmt.span],
                        [(stmt.span, "`give` is only for block expressions, not function bodies")]
                    )
                else:
                    flow.has_given = True
                    flow.give_type = self.infer_expr(stmt.value, scope)
                    if isinstance(flow.give_type, tuple): flow.give_type = flow.give_type[0]
                    flow.give_span = stmt.span
                    
            elif isinstance(stmt, IfForm):
                if_flow = self.check_if_form(stmt, scope, is_expr=False)
                if if_flow.has_returned:
                    flow.has_returned = True
                    flow.possible_not_return.extend(if_flow.possible_not_return)
            
            elif isinstance(stmt, WhileForm):
                self.loop_depth += 1
                while_flow = self.check_while_form(scope, stmt)
                self.loop_depth -= 1
                
                if while_flow.has_returned:
                    flow.possible_not_return.extend(while_flow.possible_not_return)
            
            elif isinstance(stmt, BreakStmt):
                if self.loop_depth == 0:
                    self.diag.emit( ErrorCode.E3012, {"keyword" : "break" }, [stmt.span], 
                    [(stmt.span, "can only be used in loops")])
                else:
                    flow.has_broken = True
            
            elif isinstance(stmt, ContinueStmt):
                if self.loop_depth == 0:
                    self.diag.emit( ErrorCode.E3012, {"keyword" : "break" }, [stmt.span], 
                    [(stmt.span, "can only be used in loops")])
                else:
                    flow.has_continued = True
                    
            elif isinstance(stmt, FuncForm):
                if is_func_body:
                    self.diag.emit(
                        ErrorCode.E3017, { "inner_name" : stmt.name }, [stmt.span_name],
                        [[stmt.span_name, "nested functions are forbidden"]]
                    )
                else:
                    self.check_func_form(stmt, scope)
                
            elif isinstance(stmt, ReturnStmt):
                if is_func_body:
                    flow.has_global_returned = True

                flow.has_returned = True
                flow.return_type = self.check_return_stmt(stmt, scope)
                
            elif isinstance(stmt, CallFunc):
                self.check_call_func(stmt, scope)
                
            elif isinstance(stmt, AssignmentFieldStmt):
                path = []
                current = stmt.object_name
                while isinstance(current, FieldExpr):
                    path.insert(0, current)
                    current = current.object_name
                
                symbol_object = scope.get_symbol(current.name)
                if symbol_object is None:
                    self.diag.emit(
                        ErrorCode.E3030, { "name" : current.name }, [current.span], [(current.span, "`{name}` does not exist in this scope")]
                    )
                    continue
                
                scope_object = symbol_object.scope_object
                if symbol_object.scope_object is None:
                    self.diag.emit(
                        ErrorCode.E3031, { "name" : current.name }, [current.span], [(current.span, "`{name}` is not a struct object")]
                    )
                    continue
                
                for i, obj in enumerate(path):
                    
                    if not scope_object.exist_here(obj.field):
                        self.diag.emit(
                            ErrorCode.E3032, { "struct_name" : symbol_object.zontype.name, "field" : obj.field }, [obj.span],
                            [(obj.span, "`{field}` does not exist in `{struct_name}`")]
                        )
                        continue
                    
                    symbol_object: Symbol = scope_object.get_symbol(obj.field)
                
                    if symbol_object is None:
                        self.diag.emit(
                            ErrorCode.E3031, { "name" : obj.field }, [obj.span],
                            [(obj.span, "`{name}` is not a struct object")] 
                        )
                        return
                    
                    scope_object = symbol_object.scope_object

                if not scope_object.exist_here(stmt.field_assign.name):
                    self.diag.emit(
                        ErrorCode.E3033, { "field" : stmt.field_assign.name }, [stmt.field_assign.span],
                        [(stmt.field_assign.span), "`{field}` is not a valid field for assignment here"]
                    )
                    continue
                
                self.check_assignment_stmt(stmt.field_assign, scope, True, scope_field=scope_object)
                
            if flow.has_returned or flow.has_given or flow.has_broken or flow.has_continued:
                if i < len_stmts - 1:
                    
                    if isinstance(stmt, GiveStmt):
                        self.diag.emit(
                            ErrorCode.W3001, None, [stmt.span, stmts[-1].span],
                            [(stmt.span, "this `give` exits the current block expr"), (stmts[-1].span, "...so this code will never be executed.")]
                        )
                        break
                    
                    if isinstance(stmt, ReturnStmt) and is_func_body:
                        self.diag.emit(
                            ErrorCode.W3005, { "aux" : '}'}, [stmt.span, stmts[-1].span],
                            [(stmt.span, "this `return` exits the current function"), (stmts[-1].span, "...so this code will never be executed.")]
                        )
                        break
                    
                    if isinstance(stmt, (BreakStmt, ContinueStmt)):
                        keyword = "break" if isinstance(stmt, BreakStmt) else "continue"
                        self.diag.emit(
                            ErrorCode.W3006, { "keyword" : keyword }, [stmt.span, stmts[-1].span],
                            [(stmt.span, "this `{keyword}` exits the current loop"), (stmts[-1].span, "...so this code will never be executed.")]
                        )
                        break

        return flow
    
    def check_struct_form(self,node: StructForm):
        for stmt in node.block_expr.stmts:
            if isinstance(stmt, DeclarationStmt):
                if stmt.name in node.block_expr.scope.values:
                    field_exist = node.block_expr.scope.get_symbol(stmt.name)
                    self.diag.emit(
                        ErrorCode.E3044, { "name" : stmt.name }, [stmt.span_name, field_exist.decl_span],
                        [(stmt.span_name, "`{name}` is already declared as a field in this struct"), (field_exist.decl_span, "The name has already been taken by this declaration.")]
                    )
                    continue
                
                self.check_declaration_stmt(stmt, node.block_expr.scope)
            
            elif isinstance(stmt, AssignmentStmt):
                if not node.block_expr.scope.exist_here(stmt.name):
                    self.diag.emit(
                        ErrorCode.E3045, { "name" : stmt.name }, [stmt.span_name],
                        [(stmt.span_name, "`{name}` is not a field of this struct")]
                    )
                    continue
                
                self.check_assignment_stmt(stmt, node.block_expr.scope, True, False, True)
            else:
                self.diag.emit(
                    ErrorCode.E3046, None, [stmt.span],
                    [(Span(stmt.span.end-1, stmt.span.end, self.file_map), "only field declarations and assignments are allowed inside a struct")]
                )
                continue
        
        self.TYPE_TABLE[node.name] = (node.zontype, node.block_expr.scope)          
        
    def check_return_stmt(self, node: ReturnStmt, scope: Enviroment) -> ZonType:
        if self.current_func is None:
            self.diag.emit(
                ErrorCode.E3014, None, [node.span],
                [(node.span, "this `return` is not inside a function scope")]
            )
            return ZonType(0, "UNKNOWN")
                
        type_expr = ZonType(5, "void") if node.value is None else self.infer_expr(node.value, scope)
        if isinstance(type_expr, tuple): type_expr = type_expr[0]
        
        if type_expr.num != self.current_func.return_type.num:
            self.diag.emit(
                ErrorCode.E3015,
                { "func_name" : self.current_func.name_span.to_string(),
                  "found" : type_expr.name.lower(),
                  "expected" : self.current_func.return_type.name},
                [node.span],
                [(node.span, "expected `{expected}`, found `{found}`")]
            )
        return type_expr
        
    def check_func_form(self, node: FuncForm, scope: Enviroment):
        prev_func = self.current_func
        self.current_func = scope.get_symbol(node.name)
        
        if not node.params is None:
            for param in node.params:
                symbol = node.block_expr.scope.get_symbol(param.name)
                exist_symbol = node.block_expr.scope.exist_here(param.name)
                if exist_symbol and isinstance(symbol, Symbol):
                    self.diag.emit(
                        ErrorCode.E3027, { "name" : param.name }, [param.span, symbol.decl_span],
                        [(param.span_name, "`{name}` is already declared as a parameter"), (symbol.decl_span, "`{name}` was declared here")]
                    )
                    continue
                
                param_to_decl = DeclarationStmt(
                    param.name,
                    param.mut,
                    param.zontype,
                    param.span_name,
                    param.span
                )
                
                self.check_declaration_stmt(param_to_decl, node.block_expr.scope, (param.default is None))
                
                if not param.default is None:
                    param_to_assign = AssignmentStmt(
                        param.name,
                        param.default,
                        param.span,
                        param.span_name
                    )
                    self.check_assignment_stmt(param_to_assign, node.block_expr.scope, True, True)
        
        
        flow = self.evaluate_statements(node.block_expr.stmts, node.block_expr.scope, span_block=node.span, is_func_body=True)
        
        if not flow.has_global_returned and len(flow.possible_not_return) > 0 and node.return_type != 0:
            for error_span in flow.possible_not_return:
                self.diag.emit(
                    ErrorCode.E3019, { "func_name" : node.name }, [error_span["span"]],
                    [(Span(error_span["span"].end-1, error_span["span"].end, self.file_map), "missing 'else' or a global 'return' after this if form")]
                )
                
        self.current_func = prev_func
    
    def check_call_func(self, node: CallFunc, scope: Enviroment):
        func_symbol: FuncSymbol = scope.get_symbol(node.name)
        there_is_error = False
        
        if func_symbol is None or isinstance(func_symbol, Symbol):
            self.diag.emit(ErrorCode.E3020, { "name" : node.name }, [node.span], [(node.span, "cannot call `{name}` because it has not been defined")])
            if not there_is_error: there_is_error = True
            return
        
        if func_symbol.is_native and func_symbol.is_varidic:
            if not node.params is None:
                for expr in node.params:
                    self.infer_expr(expr, scope)
            return
        
        func_params = {}
        if not func_symbol.params is None:
            for param in func_symbol.params:
                is_default = False if param.default is None else True
                func_params.update({param.name: [False, 0, is_default]})
        
        if not node.params is None:
            if len(func_params) == 0:
                self.diag.emit(ErrorCode.E3021, None, [node.span, func_symbol.name_span],
                [(node.span, "these parameters are not expected here"), (func_symbol.name_span, "this function is defined with no parameters")])
                if not there_is_error: there_is_error = True
                return
            
            for i, param in enumerate(node.params):
                zontype_param = self.infer_expr(param, scope)
                if isinstance(zontype_param, tuple): zontype_param = zontype_param[0]
                if zontype_param.num == 0: continue
                func_param = func_symbol.params[i]
                
                if zontype_param.num != func_param.zontype.num:
                    self.diag.emit(ErrorCode.E3022, { "found" : zontype_param.name, "expect" : func_param.zontype.name},
                    [param.span], [(param.span, "this expression is `{found}` but the parameter expects `{expect}`")])
                    if not there_is_error: there_is_error = True
                    continue
                
                func_params[func_param.name][0] = True
                func_params[func_param.name][1] = i
                
        if not node.keyparams is None:
            if len(func_params) == 0:
                self.diag.emit(ErrorCode.E3021, None, [func_symbol.name_span, node.span],
                [(func_symbol.name_span, "this function is defined with no parameters"), (node.span, "these parameters are not expected here")])
                if not there_is_error: there_is_error = True
                return
                        
            for key, value in node.keyparams.items():
                zontype_param = self.infer_expr(value[0], scope)
                if isinstance(zontype_param, tuple): zontype_param = zontype_param[0]
                if zontype_param.num == 0: return
                
                func_param = None
                for i in range(len(func_symbol.params)):
                    if key == func_symbol.params[i].name:
                        func_param = func_symbol.params[i]
                
                if func_param is None:
                    self.diag.emit(ErrorCode.E3023, { "name" : node.name, "name_param" : key },
                    [value[1]], [(value[2], "this parameter does not exist in `{name}`")])
                    if not there_is_error: there_is_error = True
                    continue
                
                if func_params[func_param.name][0]:
                    self.diag.emit(ErrorCode.E3024, { "name_func" : node.name, "name_param" : key, "param_pos" : func_params[func_param.name][1] },
                    [value[1]], [(value[1], "this parameter already received a value")])
                    if not there_is_error: there_is_error = True
                    continue
                
                if zontype_param.num != func_param.zontype.num:
                    self.diag.emit(ErrorCode.E3022, { "found" : zontype_param.name, "expect" : func_param.zontype.name},
                    [param.span], [(param.span, "this expression is `{found}` but the parameter expects `{expect}`")])
                    if not there_is_error: there_is_error = True
                    continue
                
                func_params[func_param.name][0] = True
        
        missing_params = 0
        for key, value in func_params.items():
            if not value[0] and not value[2]:
                missing_params += 1
        
        if missing_params > 0 and not there_is_error:
            self.diag.emit(ErrorCode.E3025, { "name_func" : node.name, "num" : missing_params }, [node.span_name],
            [(node.span_name, "missing {num} required parameter(s)")])
            
    def check_declaration_stmt(self, node: DeclarationStmt, scope: Enviroment, is_param = False):
        get = scope.get_symbol(node.name)
        if not(get is None) and isinstance(get, FuncSymbol):
            self.diag.emit(
                ErrorCode.E3013, { "name": node.name, "kind": "variable"},
                [node.span_name, get.name_span],
                [(node.span_name, "this name is already in use"), (get.name_span, "first defined as a function here")]
            )
            return
        
        scope.define(node.name, Symbol(node.mut, node.type, not is_param, node.span))
            
    def check_assignment_stmt(self, node: AssignmentStmt, scope: Enviroment, not_empty: bool, is_param = False, is_field = False, scope_field: Enviroment = None):
        symbol = None
        if scope_field is None:
            symbol = scope.get_symbol(node.name)
        else:
            symbol = scope_field.get_symbol(node.name)
            
        if symbol is None:
            self.diag.emit(ErrorCode.E3001, { "name" : node.name }, [node.span], [(node.span_name, "does not exist in this scope")])
            return
        
        if isinstance(symbol, FuncSymbol): return
        
        if not symbol.mutability and not symbol.is_empty:
            self.diag.emit(ErrorCode.E3005, { "name" : node.name }, [node.span, symbol.decl_span],
            [(node.span_name, "is immutable, it was already assigned a value"), (symbol.decl_span, "was first defined as immutable here")])
            return
        
        
        if self.loop_depth > 0 and not(scope.exist_here(node.name)) and not(symbol.mutability) and symbol.is_empty:
            self.diag.emit(ErrorCode.E3016, None, [node.span], [(node.span_name, "cannot initialize an outer `inmut` variable here")])
            return
        
        value_type = self.infer_expr(node.value, scope, is_field, node.name)
        if isinstance(value_type, tuple):
            symbol.scope_object = value_type[1]
            value_type = value_type[0]
            
        if value_type.num == 0: return
        
        if symbol.zontype.num == 0:
            symbol.zontype = value_type
            
        elif symbol.zontype.num != value_type.num:
            err_span = node.value.stmts[node.value.give_address].value.span if isinstance(node.value, BlockExpr) else node.value.span
            self.diag.emit(
                ErrorCode.E3006,
                { "name" : node.name, "expected_type" : symbol.zontype.name, "found_type" : value_type.name},
                [node.span],
                [(err_span, "this expression returns '{found_type}', but '{name}' expects '{expected_type}'")]
            )
            return
    
        if symbol.is_empty and not_empty and not is_param:
            symbol.is_empty = False
                
    def check_if_form(self, if_node: IfForm, scope: Enviroment, is_expr: bool) -> FlowResult | list:
        sym_empty_count = DictTemp({})
        values_give = []
        flow = FlowResult()

        def eval_branch(branch, is_expr_branch, is_else) -> FlowResult:
            if isinstance(branch.cond, BoolLiteral) and not is_else:
                has_unreachable = (if_node.elif_branches or if_node.else_branch)
                if branch.cond.value == 1 and has_unreachable:
                    self.diag.emit(ErrorCode.W3002, None, [branch.cond.span], [(branch.cond.span, "this condition is always `true`")])
                elif branch.cond.value == 0:
                    self.diag.emit(ErrorCode.W3003, None, [branch.cond.span], [(branch.cond.span, "this condition is always `false`")])
            
            check_cond = True
            if is_else:
                check_cond = False
            
            return self.check_if_branch(branch, scope, sym_empty_count, check_cond, is_expr_branch)

        if_branch_flow = eval_branch(if_node.if_branch, is_expr, False)
        if is_expr and if_branch_flow.has_given: values_give.append((if_branch_flow.give_type, if_branch_flow.give_span))
        if if_branch_flow.has_returned: flow.has_returned = True
        
        if if_node.else_branch is None:
            if flow.has_returned:
                flow.possible_not_return.append({"span" : if_node.span})
            
            if len(sym_empty_count.dict_temp) > 0:
                last_branch_span = if_node.elif_branches[-1].span if if_node.elif_branches else if_node.if_branch.span
                self.diag.emit(ErrorCode.E3008, None, [last_branch_span], [(Span(last_branch_span.end-1, last_branch_span.end, self.file_map), "an `else` branch was expected here")])
                return flow
                
        if if_node.elif_branches:
            for elif_node in if_node.elif_branches:
                elif_flow = eval_branch(elif_node, is_expr, False)
                if is_expr and elif_flow.has_given: values_give.append((elif_flow.give_type, elif_flow.give_span))
                if elif_flow.has_returned and flow.has_returned and elif_flow.return_type != if_branch_flow.return_type:
                    flow.possible_not_return.append({"span": if_node.span})

        if if_node.else_branch:
            else_flow = eval_branch(if_node.else_branch, is_expr, True)
            if is_expr and else_flow.has_given: values_give.append((else_flow.give_type, else_flow.give_span))

        if len(sym_empty_count.dict_temp) > 0:
            for symbol, branches_span in sym_empty_count.dict_temp.items():
                if branches_span[0] < if_node.len_branch:
                    self.diag.emit(
                        ErrorCode.E3009, { "name" : symbol }, [if_node.span, branches_span[1]],
                        [(Span(if_node.span.end-1, if_node.span.end, self.file_map), "`{name}` is first assigned inside this if form, but not in every branch"),
                         (branches_span[1], "`{name}` is declared empty here and may still be empty after the if form")]
                    )
                else:
                    scope.get_symbol(symbol).is_empty = False
        
        return values_give if is_expr else flow
                
    def check_if_branch(self, if_branch: IfBranch, scope_back: Enviroment, sym_empty_count: DictTemp, check_cond: bool, is_expr: bool) -> FlowResult:
        if check_cond:
            type_condition = self.infer_expr(if_branch.cond, scope_back)
            if isinstance(type_condition, tuple): type_condition = type_condition[0]
            if type_condition.num != 3:
                self.diag.emit(
                    ErrorCode.E3007, { "found_type" : type_condition.name },
                    [Span(if_branch.span.start, if_branch.cond.span.end, self.file_map)],
                    [(if_branch.cond.span, "this expression returns `{found_type}`, but a condition field expects `bool`")]
                )

        return self.evaluate_statements(if_branch.block.stmts, if_branch.block.scope, span_block=if_branch.block.span, is_expr=is_expr, sym_empty_count=sym_empty_count)
                
    def check_while_form(self, scope: Enviroment, while_node: WhileForm) -> FlowResult:
        type_condition = self.infer_expr(while_node.condition_field, scope)
        if isinstance(type_condition, tuple): type_condition = type_condition[0]
        if type_condition.num != 3:
            self.diag.emit(
                ErrorCode.E3007, { "found_type" : type_condition.name },
                [Span(while_node.span.start, while_node.condition_field.span.end, self.file_map)],
                [(while_node.condition_field.span, "this expression returns `{found_type}`, but a condition field expects `bool`")]
            )
            
        flow = self.evaluate_statements(while_node.block_expr.stmts, while_node.block_expr.scope, while_node.block_expr.span)
        
        if isinstance(while_node.condition_field, BoolLiteral):
            if while_node.condition_field.value == 1:
                if not flow.has_broken:
                    self.diag.emit(
                        ErrorCode.W3004, None, [while_node.span],
                        [(Span(while_node.span.end - 1, while_node.span.end, self.file_map), "this loop has no exit point")]
                    )
            else:
                self.diag.emit(
                    ErrorCode.W3003, None, [while_node.condition_field.span],
                    [(while_node.condition_field.span, "this condition is always `false`")]
                )
        return flow
            
    def check_operands_type(self, operands_type: tuple, return_type: ZonType, equal: bool, operator: str, *zontypes):    
        len_types = len(zontypes)
        for i in range(len(operands_type)):
            no_match = sum(1 for j in range(len_types) if operands_type[i][0].num != zontypes[j].num)
            
            if no_match == len_types:
                valid_types = ", ".join(t.name for t in zontypes[:-1])
                if len_types > 1: valid_types += f" or {zontypes[-1].name}"
                else: valid_types = zontypes[0].name
                
                self.diag.emit(
                    ErrorCode.E3003,
                    { "operator": operator, "valid_types": valid_types, "found_type": operands_type[i][0].name},
                    [operands_type[i][1]],
                    [(operands_type[i][1], "this operand is `{found_type}`, but `{operator}` expects {valid_types}")]
                )
                return ZonType(0, "UNKNOWN")
                
        if equal and operands_type[0][0].num != operands_type[1][0].num:
            self.diag.emit(
                ErrorCode.E3004,
                { "operator": operator, "right_type": operands_type[1][0].name, "left_type": operands_type[0][0].name},
                [operands_type[1][1]],
                [(operands_type[1][1], "this is `{right_type}`, but `{operator}` expects `{left_type}` to match the left operand")]
            )
            return ZonType(0, "UNKNOWN")
            
        return return_type
                
    def infer_expr(self, expr: NodeExpr, scope: Enviroment, is_field = False, name: str | None = None) -> ZonType:
        zontype_err = ZonType(0, "UNKNOWN")
    
        if isinstance(expr, IntLiteral): return ZonType(1, "int")
        elif isinstance(expr, FloatLiteral): return ZonType(2, "float")
        elif isinstance(expr, BoolLiteral): return ZonType(3, "bool")
        elif isinstance(expr, StringLiteral): return ZonType(4, "string")
        
        elif isinstance(expr, BinaryExpr):
            op = expr.operator
            left_type = self.infer_expr(expr.left, scope, name=name)
            if isinstance(left_type, tuple): left_type = left_type[0]
            right_type = self.infer_expr(expr.right, scope, name=name)
            if isinstance(right_type, tuple): right_type = right_type[0]
            
            if left_type.num == 0 or right_type.num == 0: return zontype_err
            
            if op in (Operator.ADD, Operator.SUB, Operator.MUL, Operator.POW, Operator.MOD, Operator.DIV):
                op_str = {Operator.ADD: '+', Operator.SUB: '-', Operator.MUL: '*', Operator.DIV: '/', Operator.MOD: '%', Operator.POW: "**"}[op]
                return self.check_operands_type(((left_type, expr.left.span), (right_type, expr.right.span)), left_type, True, op_str, ZonType(1, "int"), ZonType(2, "float"))
            
            elif op in (Operator.LT, Operator.GT, Operator.LE, Operator.GE):
                op_str = {Operator.LT: '<', Operator.GT: '>', Operator.LE: '<=', Operator.GE: '>='}[op]
                return self.check_operands_type(((left_type, expr.left.span), (right_type, expr.right.span)), ZonType(3, "bool"), True, op_str, ZonType(1, "int"), ZonType(2, "float"))
            
            elif op in (Operator.AND, Operator.OR):
                op_str = {Operator.AND: 'and/&&', Operator.OR: 'or/||'}[op]
                return self.check_operands_type(((left_type, expr.left.span), (right_type, expr.right.span)), left_type, False, op_str, ZonType(3, "bool"))
            
            elif op in (Operator.EQ, Operator.NE):
                op_str = {Operator.EQ: '==', Operator.NE: '!='}[op]
                return self.check_operands_type(((left_type, expr.left.span), (right_type, expr.right.span)), ZonType(3, "bool"), True, op_str, ZonType(1, "int"), ZonType(2, "float"), ZonType(3, "bool"), ZonType(4, "string"))
                
        elif isinstance(expr, UnaryExpr):
            op = expr.operator
            value_type = self.infer_expr(expr.value, scope, name=name)
            if isinstance(value_type, tuple): value_type = value_type[0]
            if value_type.num == 0: return zontype_err
            
            if op == Operator.NEG:
                return self.check_operands_type(((value_type, expr.value.span),), value_type, False, '-', ZonType(1, "int"), ZonType(2, "float"))
            else:
                return self.check_operands_type(((value_type, expr.value.span),), value_type, False, 'not/!', ZonType(3, "bool"))
        
        elif isinstance(expr, VariableExpr):
            symbol = scope.get_symbol(expr.name)
            if symbol is None:
                self.diag.emit(ErrorCode.E3001, { "name" : expr.name }, [expr.span], [(expr.span, "does not exist in this scope")])
                return zontype_err
            
            elif symbol.is_empty:
                self.diag.emit(ErrorCode.E3002, { "name" : expr.name }, [expr.span], [(expr.span, "has no value at this point")])
                return zontype_err
            
            if not symbol.scope_object is None:
                return (symbol.zontype, copy.deepcopy(symbol.scope_object))
                
            return symbol.zontype
        
        elif isinstance(expr, FieldExpr):
            path = []
            current = expr
            
            while isinstance(current, FieldExpr):
                path.insert(0, current)
                current = current.object_name
            
            symbol_object = scope.get_symbol(current.name)
            if symbol_object is None:
                self.diag.emit(
                    ErrorCode.E3030, { "name" : current.name }, [current.span], [(current.span, "`{name}` does not exist in this scope")]
                )
                return zontype_err
            
            scope_object = self.TYPE_TABLE.get(symbol_object.zontype.name)
            
            if scope_object is None:
                self.diag.emit(
                    ErrorCode.E3031, { "name" : current.name }, [current.span], [(current.span, "`{name}` is not a struct object")]
                )
                return zontype_err
            
            scope_object = scope_object[1]
            for i, obj in enumerate(path):
                if i == len(path)-1:
                    break
                
                if not scope_object.exist_here(obj.field):
                    self.diag.emit(
                        ErrorCode.E3032, { "struct_name" : symbol_object.zontype.name, "field" : obj.field }, [obj.span],
                        [(obj.span, "`{field}` does not exist in `{struct_name}`")]
                    )
                    return zontype_err
                
                symbol_object = self.TYPE_TABLE.get(scope_object.get_symbol(obj.field).zontype.name)
            
                if symbol_object is None:
                    self.diag.emit(
                        ErrorCode.E3031, { "name" : obj.field }, [obj.span],
                        [(obj.span, "`{name}` is not a struct object")] 
                    )
                    return zontype_err
                
                scope_object = symbol_object[1]

            if not scope_object.exist_here(path[-1].field):
                self.diag.emit(
                    ErrorCode.E3040, { "field" : path[-1].field }, [path[-1].span],
                    [(path[-1].span, "`{field}` does not exist here")]
                )
                return zontype_err
            
            field_symbol: Symbol = scope_object.get_symbol(path[-1].field)
            if field_symbol.scope_object is None:
                return field_symbol.zontype
            else:
                return (field_symbol.zontype, field_symbol.scope_object)
        
        elif isinstance(expr, ConstructExpr):
            struct_blueprint: Enviroment = self.TYPE_TABLE.get(expr.name_struct)
            
            if struct_blueprint is None:
                span_err = Span(expr.span.start, expr.span.start + 1, self.file_map)
                self.diag.emit(
                    ErrorCode.E3038, { "name" : expr.name_struct }, [span_err],
                    [(span_err, "`{name}` is not a declared struct")]
                )
                return zontype_err
            
            len_list_assign = 0 if expr.list_assign is None else len(expr.list_assign)
            len_dict_assign = 0 if expr.dict_assign is None else len(expr.dict_assign)
            
            if len(struct_blueprint[1].values) < len_list_assign + len_dict_assign:
                span_err = Span(expr.span.start, expr.span.start+1, self.file_map)
                self.diag.emit(
                    ErrorCode.E3037, { "struct_name" : expr.name_struct, "max" : len(struct_blueprint), "found" : len_list_assign + len_dict_assign },
                    [span_err], [(span_err, "too many values for `{struct_name}`")]
                )
                return zontype_err
            
            struct_blueprint = struct_blueprint[1]
            struct_fields = {}
            field_list: list[tuple[str, Symbol]] = []
            
            copy_blueprint = Enviroment()
            copy_blueprint.values = copy.deepcopy(struct_blueprint.values)
            
            for i, (key, value) in enumerate(copy_blueprint.values.items()):
                is_default = not value.is_empty
                struct_fields.update({key: [False, 0, is_default]})
                field_list.append((key, value))
            
            if not expr.list_assign is None:
                for i, field in enumerate(expr.list_assign):
                    zontype_field = self.infer_expr(field, scope, name=name)
                    if isinstance(zontype_field, tuple):
                        field_list[i][1].scope_object = zontype_field[1]
                        zontype_field = zontype_field[0]
                    
                    field_struct = field_list[i]
                    
                    if not field_struct[1].mutability and not field_struct[1].is_empty:
                        self.diag.emit(
                            ErrorCode.E3034, { "field" : field_struct[0] }, [field.span, field_struct[1].decl_span],
                            [(field.span, "`{field}` is inmutable and cannot be reassigned"), (field_struct[1].decl_span, "here it was declared as `inmut`")]
                        )
                        continue
                    
                    if field_struct[1].zontype == 0:
                        field_struct[1].zontype = zontype_field
                        
                    elif zontype_field.num != field_struct[1].zontype.num:
                        self.diag.emit(
                            ErrorCode.E3029, { "field" : field_struct[0] , "expected" : field_struct[1].zontype.name , "found" : zontype_field.name },
                            [field.span], [(field.span, "this expression returns `{found}`, but `{field}` expects `{expected}`")]
                        )
                        continue
                    
                    struct_fields[field_struct[0]][0] = True
                    struct_fields[field_struct[0]][1] = i
                    field_struct[1].is_empty = False
                    
            if not expr.dict_assign is None:
                for key, value in expr.dict_assign.items():
                    zontype_field = self.infer_expr(value[0], scope, name=name)
                    
                    field_struct = None
                    for i in range(len(field_list)):
                        if key == field_list[i][0]:
                            field_struct = field_list[i]
                            
                    if isinstance(zontype_field, tuple):
                        field_struct[1].scope_object = zontype_field[1]
                        zontype_field = zontype_field[0]
                    
                    if field_struct is None:
                        self.diag.emit(
                            ErrorCode.E3036, { "field" : key, "struct_name" : expr.struct_type.name },
                            [value[2]], [(value[2], "`{field}` does not exist in `{struct_name}`")]
                        )
                        continue
                    
                    if struct_fields[field_struct[0]][0]:
                        self.diag.emit(
                            ErrorCode.E3035, { "field" : key }, [value[2]],
                            [(value[2], "`{field}` was already assigned in this construct")]
                        )
                        continue
                    
                    if not field_struct[1].mutability and not field_struct[1].is_empty:
                        self.diag.emit(
                            ErrorCode.E3034, { "field" : field_struct[0] }, [value[1], field_struct[1].decl_span],
                            [(value[1], "`{field}` is inmutable and cannot be reassigned"), (field_struct[1].decl_span, "here it was declared as `inmut`")]
                        )
                        continue
                    
                    if field_struct[1].zontype.num == 0:
                        field_struct[1].zontype = zontype_field
                        
                    elif zontype_field.num != field_struct[1].zontype.num:
                        self.diag.emit(
                            ErrorCode.E3029, { "field" : field_struct[0] , "expected" : field_struct[1].zontype.name , "found" : zontype_field.name },
                            [value[1] ], [(value[1], "this expression returns `{found}`, but `{field}` expects `{expected}`")]
                        )
                        continue
                    
                    struct_fields[field_struct[0]][0] = True
                    field_struct[1].is_empty = False
                    
            return (self.TYPE_TABLE[expr.name_struct][0], copy_blueprint)
        
        elif isinstance(expr, BlockExpr):
            if is_field:
                span_err = Span(expr.span.end-1, expr.span.end, self.file_map)
                self.diag.emit(
                    ErrorCode.E3028, None, [span_err], [(span_err, "this expression is not allowed as a field default value")]
                )
                return zontype_err
            
            self.evaluate_statements(expr.stmts, expr.scope, span_block=expr.span, is_expr=True)
            return self.infer_expr(expr.stmts[expr.give_address].value, expr.scope, name=name)

        elif isinstance(expr, IfForm):
            if is_field:
                span_err = Span(expr.span.end-1, expr.span.end, self.file_map)
                self.diag.emit(
                    ErrorCode.E3028, None, [span_err], [(span_err, "this expression is not allowed as a field default value")]
                )
                return zontype_err
            
            if expr.else_branch is None:
                last_branch_span = expr.elif_branches[-1].span if expr.elif_branches else expr.if_branch.span
                self.diag.emit(ErrorCode.E3010, None, [last_branch_span], [(Span(last_branch_span.end - 1, last_branch_span.end, self.file_map), "an `else` branch is required here when the if form is used as an expression")])
                return zontype_err
            
            give_values = self.check_if_form(expr, scope, is_expr=True)
            type_first, errors_span, codes_span = None, [], []
            
            for i, val in enumerate(give_values):
                if i == 0:
                    type_first = val[0]
                    continue
                if val[0].num != type_first.num:
                    errors_span.append((val[1], f"this `give` returns `{val[0].name}`, but the if form expects `{type_first.name}`"))
                    codes_span.append(val[1])
            
            if codes_span:
                self.diag.emit(ErrorCode.E3011, None, codes_span, errors_span)
                return zontype_err
            return type_first

        elif isinstance(expr, CallFunc):
            if is_field:
                span_err = Span(expr.span.end-1, expr.span.end, self.file_map)
                self.diag.emit(
                    ErrorCode.E3028, None, [span_err], [(span_err, "this expression is not allowed as a field default value")]
                )
                return zontype_err
            
            self.check_call_func(expr, scope)
            func_symbol = scope.get_symbol(expr.name)
            if func_symbol is None: return zontype_err
            if func_symbol.return_type == ZonType(5, "void"):
                self.diag.emit(ErrorCode.E3026, { "name" : expr.name }, [expr.span_name], [(expr.span_name, "this call returns `void`")])
                return zontype_err
            return func_symbol.return_type
            
        return zontype_err