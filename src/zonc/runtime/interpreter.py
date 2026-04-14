from zonc.zonast import *
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from .runtime_scope import RuntimeScope, RuntimeValue, RuntimeFunc, RuntimeStruct
from zonc.location_file import Span
from dataclasses import dataclass
from zonc.zonstdlib import *
from copy import deepcopy


@dataclass
class CallFrame:
    func_name: str
    scope: RuntimeScope
    depth: int
    firm: str

class BreakSignal(Exception): pass


class ContinueSignal(Exception): pass


class GiveSignal(Exception):
    def __init__(self, value: NodeExpr):
        self.value = value
        

class ReturnSignal(Exception):
    def __init__(self, value: NodeExpr | None):
        self.value = value


class ZoneticRuntimeError(Exception):
    def __init__(
        self,
        error_code: ErrorCode,
        args: dict[str, str] | None,
        span_code: list[Span] | None,
        span_error: list[tuple[Span, str]] | None,
        call_stack: list[CallFrame] | None = None,
        traceback: bool = False,
    ):
        self.error_code = error_code
        self.span_code = span_code
        self.span_error = span_error
        self.arg = args
        self.call_stack = call_stack
        self.traceback = traceback


class Interpreter:
    def __init__(self, diag: DiagnosticEngine) -> None:
        self.diag = diag
        self.scope_main: RuntimeScope = None
        self.MAX_DEPTH = 200
        self.call_stack: list[CallFrame] = []
        self.current_depth_function = 0
        
        
    NATIVE = {
        "print": Native(_print),
        "readInt": Native(_read_int),
        "readFloat": Native(_read_float),
        "readString": Native(_read_string)
    }
    
    
    def execute(self, program: Program) -> None:
        scope = RuntimeScope()
        self.scope_main = scope
        self.pre_scan(program.stmts, scope)
        for node in program.stmts:
            self.exec_stmt(node, scope)
            
    
    def pre_scan(self, stmts: list[Node], scope: RuntimeScope):
        for stmt in stmts:
            match stmt:
                case FuncForm():
                    scope.set(
                        stmt.name,
                        RuntimeFunc(stmt.block_expr, stmt.params)
                    )
                    
                case StructForm():
                    scope_struct = RuntimeScope()
                    for stmt_struct in stmt.block_expr.stmts:
                        self.exec_stmt(stmt_struct, scope_struct)
                        
                    scope.set(
                        stmt.name,
                        RuntimeStruct(scope_struct)
                    )
                    
    def exec_stmt(self, node: Node, scope: RuntimeScope) -> None:
        match node:
            case DeclarationStmt():
                scope.set(
                    node.name,
                    RuntimeValue(
                        None
                    )
                )
            
            case AssignmentStmt():
                scope.update(
                    node.name,
                    self.eval_expr(node.value, scope)
                )
                
            case AssignmentFieldStmt():
                path_struct = []
                current = node.object_name
                while not isinstance(current, VariableExpr):
                    path_struct.insert(0, current.field)
                    current = current.object_name
                    
                first_object = scope.get(current.name)
                actual_scope = first_object.value.scope_struct
                
                for i, p in enumerate(path_struct):
                    actual_scope = actual_scope.get(p).value.scope_struct
                    
                actual_scope.update(
                    node.field_assign.name,
                    self.eval_expr(node.field_assign.value, scope)
                )
                
            case BreakStmt():
                raise BreakSignal
            
            case ContinueStmt():
                raise ContinueSignal
            
            case GiveStmt():
                raise GiveSignal(self.eval_expr(node.value, scope))
            
            case ReturnStmt():
                raise ReturnSignal(self.eval_expr(node.value, scope))
                
            case BlockExpr():
                block_scope = RuntimeScope(scope)
                
                try:
                    for stmt in node.stmts:
                        self.exec_stmt(stmt, block_scope)
                            
                except GiveSignal:
                    return
                
                except ReturnSignal as ret:
                    raise ReturnSignal(ret.value)
                    
            case IfForm():
                try:
                    if self.eval_expr(node.if_branch.cond, scope):
                        return self.exec_stmt(node.if_branch.block, scope)
                        
                    if not(node.elif_branches is None):
                        for branch in node.elif_branches:
                            if self.eval_expr(branch.cond, scope):
                                return self.exec_stmt(branch.block, scope)
                    
                    if not(node.else_branch is None):
                        return self.exec_stmt(node.else_branch.block, scope)
                
                except ReturnSignal as ret:
                    raise ReturnSignal(ret.value)
            
            case WhileForm():
                while self.eval_expr(node.condition_field, scope):
                    iter_scope = RuntimeScope(scope)
                    try:
                        for stmt in node.block_expr.stmts:
                            self.exec_stmt(stmt, iter_scope)
                            
                    except BreakSignal:
                        break
                    
                    except ContinueSignal:
                        continue
                    
                    except ReturnSignal as ret:
                        raise ReturnSignal(ret.value)

            case CallFunc():
                self.exec_call_func(node, scope)
                self.current_depth_function -= 1
                self.call_stack.pop()
                if self.current_depth_function == 0:
                    self.call_stack.clear()
             
                
    def exec_call_func(self, node: CallFunc, scope: RuntimeScope):
        self.current_depth_function += 1
        current_call_frame = CallFrame(
            node.name,
            RuntimeScope(self.scope_main),
            self.current_depth_function,
            node.span.to_string()
        )
        self.call_stack.append(current_call_frame)
        
        if self.current_depth_function == self.MAX_DEPTH:
            end_call_stack = []
            for i, stack in enumerate(self.call_stack):
                if i < 5:
                    end_call_stack.append(stack)
                
            end_call_stack.append(self.call_stack[-1])
            
            raise ZoneticRuntimeError(
                ErrorCode.E4002,
                { "limit" : self.MAX_DEPTH,
                  "func" : node.name },
                None,
                [(node.span, None)],
                end_call_stack,
                True
            )
        
        if node.name in self.NATIVE:
            params_evalued = []
            if not node.params is None:
                for param in node.params:
                    params_evalued.append(self.eval_expr(param, scope))
            ret = self.NATIVE[node.name].func(params_evalued)
            if ret is None: return
            else: return ret
        
        else:
            func_symbol = self.scope_main.get(node.name)
            params_decl = func_symbol.params
            
            params_evalued = {}
            
            if not params_decl is None:
                for param in params_decl:
                    default = None if param.default is None else self.eval_expr(param.default, scope)
                    params_evalued.update({param.name : default})
            
            if not node.params is None:
                for i, param in enumerate(node.params):
                    param_decl = params_decl[i]
                    params_evalued[param_decl.name] = self.eval_expr(param, scope)
                    
            if not node.keyparams is None:
                for key, value in node.keyparams.items():
                    params_evalued[key] = self.eval_expr(value[0], scope)
                    
            for key, value in params_evalued.items():
                current_call_frame.scope.set(key, RuntimeValue(value))
            
            try:
                for stmt in func_symbol.block.stmts:
                    self.exec_stmt(stmt, current_call_frame.scope)
                return
                    
            except ReturnSignal as ret:
                return ret.value
             
                                    
    def eval_expr(self, node: NodeExpr, scope: RuntimeScope) -> any:
        match node:
            case IntLiteral(): return node.value
            case FloatLiteral(): return node.value
            case BoolLiteral(): return bool(node.value)
            case StringLiteral(): return node.value
            case BinaryExpr():
                match node.operator:
                    case Operator.ADD:
                        return self.eval_expr(node.left, scope) + self.eval_expr(node.right, scope)
                    
                    case Operator.SUB:
                        return self.eval_expr(node.left, scope) - self.eval_expr(node.right, scope)
                    
                    case Operator.MUL:
                        return self.eval_expr(node.left, scope) * self.eval_expr(node.right, scope)
                    
                    case Operator.DIV:
                        right = self.eval_expr(node.right, scope)
                        
                        if right == 0:
                            raise ZoneticRuntimeError(
                                ErrorCode.E4001,
                                { "operator" : '/' },
                                [node.right.span],
                                [(node.right.span, "this evaluates to zero at runtime")]
                            )
                            
                        if isinstance(right, int):
                            return int(self.eval_expr(node.left, scope) / right)
                            
                        return self.eval_expr(node.left, scope) / right
                    
                    case Operator.POW:
                        return self.eval_expr(node.left, scope) ** self.eval_expr(node.right, scope)
                    
                    case Operator.MOD:
                        right = self.eval_expr(node.right, scope)
                        
                        if right == 0:
                            raise ZoneticRuntimeError(
                                ErrorCode.E4001,
                                { "operator" : '%' },
                                [node.right.span],
                                [(node.right.span, "this evaluates to zero at runtime")]
                            )
                        
                        return self.eval_expr(node.left, scope) % right
                    
                    case Operator.LT:
                        return self.eval_expr(node.left, scope) < self.eval_expr(node.right, scope)
                    
                    case Operator.GT:
                        return self.eval_expr(node.left, scope) > self.eval_expr(node.right, scope)

                    case Operator.LE:
                        return self.eval_expr(node.left, scope) <= self.eval_expr(node.right, scope)
                    
                    case Operator.GE:
                        return self.eval_expr(node.left, scope) >= self.eval_expr(node.right, scope)
                    
                    case Operator.EQ:
                        return self.eval_expr(node.left, scope) == self.eval_expr(node.right, scope)
                    
                    case Operator.NE:
                        return self.eval_expr(node.left, scope) != self.eval_expr(node.right, scope)
                    
                    case Operator.AND:
                        left = self.eval_expr(node.left, scope)
                        
                        if not left:
                            return False
                        
                        return left and self.eval_expr(node.right, scope)
                    
                    case Operator.OR:
                        left = self.eval_expr(node.left, scope)
                        
                        if left:
                            return True
                        
                        return left or self.eval_expr(node.right, scope)
                
            case UnaryExpr():
                match node.operator:
                    case Operator.NOT:
                        return not(self.eval_expr(node.value, scope))
                    
                    case Operator.NEG:
                        return -(self.eval_expr(node.value, scope))
                    
            case VariableExpr():
                value = scope.get(node.name).value
                if isinstance(value, RuntimeStruct): return deepcopy(value)
                
                return value
                    
            case BlockExpr():
                try:
                    block_scope = RuntimeScope(scope)
                    for stmt in node.stmts:
                        self.exec_stmt(stmt, block_scope)
                        
                except GiveSignal as give:
                    return give.value
            
            case IfForm():
                if self.eval_expr(node.if_branch.cond, scope):
                    return self.eval_expr(node.if_branch.block, scope)
                    
                if not(node.elif_branches is None):
                    for branch in node.elif_branches:
                        if self.eval_expr(branch.cond, scope):
                            return self.eval_expr(branch.block, scope)
                        
                if not(node.else_branch is None):
                    return self.eval_expr(node.else_branch.block, scope)
            
            case CallFunc():
                value_ret = self.exec_call_func(node, scope)
                self.current_depth_function -= 1
                self.call_stack.pop()
                if self.current_depth_function == 0:
                    self.call_stack.clear()
                return value_ret
            
            case ConstructExpr():
                struct_zon = scope.get(node.name_struct)
                struct_copy = deepcopy(struct_zon)
                
                list_fields_decl = []
                for i, (key, value) in enumerate(struct_zon.scope_struct.values.items()):
                    list_fields_decl.append(key)
                
                if not node.list_assign is None:
                    for i, field_assign in enumerate(node.list_assign):
                        struct_copy.scope_struct.update(list_fields_decl[i], self.eval_expr(field_assign, scope))
                
                if not node.dict_assign is None:
                    for key, value in node.dict_assign.items():
                        struct_copy.scope_struct.update(key, self.eval_expr(value[0], scope))
                    
                return struct_copy
            
            case FieldExpr():
                path_struct = []
                current = node
                while not isinstance(current, VariableExpr):
                    path_struct.insert(0, current.field)
                    current = current.object_name
                    
                first_object = scope.get(current.name)
                actual_scope = first_object.value.scope_struct
                len_path = len(path_struct)
                
                for i, p in enumerate(path_struct):
                    if i == len_path-1:
                        return self.eval_expr(
                            VariableExpr(p, None),
                            actual_scope
                        )
                    
                    actual_scope = actual_scope.get(p).value.scope_struct
                    
            case RuntimeStruct():
                copy_object = deepcopy(node)
                return copy_object                