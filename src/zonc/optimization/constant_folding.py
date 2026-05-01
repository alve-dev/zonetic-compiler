from zonc.zonast import *
from zonc.enviroment import *
from zonc.zonc_errors import *
import struct
import math

RANGES = {
    'int32': (-2_147_483_648, 2_147_483_647),
    'int64': (-9_223_372_036_854_775_808, 9_223_372_036_854_775_807)
}

class ConstantFolding:
    def __init__(self, reporter: DiagnosticEngine):
        self.reporter = reporter
        
    def visit_Print(self, node: CallFunc, scope: Enviroment):
        # por ahora hago esto para mejorar el print
        # el print es especial por eso tendre constant folding para el
        # por ahora sera simple de operacion, cuando agruege stirngs a la vm
        # sera mas agresivo volviendo todo string si se puede
        # ademas constant folding de llamadas sera aparte
        if node.params is not None:
            span = node.params[0].span
            folded_param = self.evaluate_static_value(node.params[0], scope)
            new_param = self.transform_to_zonvalue(folded_param)
            new_param.span = span
            if isinstance(new_param, IntLiteral):
                if not self.check_range_int(new_param.value, "int64", span):
                    node.params[0] = new_param
            
            elif isinstance(new_param, FloatLiteral):
                if not self.check_range_float(new_param.value, "double", span):
                    node.params[0] = new_param
        
    
    def visit_If(self, node: IfForm, scope: Enviroment):
        folded_cond_if = self.evaluate_static_value(node.if_branch.cond, scope)
        new_cond = self.transform_to_zonvalue(folded_cond_if)
        node.if_branch.cond = new_cond
        if not node.elif_branches is None:
            for i, branch in enumerate(node.elif_branches):
                folded_cond_elif = self.evaluate_static_value(branch.cond, scope)
                new_cond = self.transform_to_zonvalue(folded_cond_elif)
                node.elif_branches[i].cond = new_cond
    
    def visit_Initialization(self, node: InitializationStmt, scope: Enviroment):
        span = node.assign_stmt.value.span
        folded = self.evaluate_static_value(node.assign_stmt.value, scope)
        new_node = self.transform_to_zonvalue(folded)
        new_node.span = span
        
        symbol = Symbol(node.decl_stmt.mut, node.decl_stmt.type, False, node.decl_stmt.span)
        scope.define(node.decl_stmt.name, symbol)
        
        if isinstance(new_node, IntLiteral):
            error = False
            if symbol.zontype.num in [1, 6]:
                error = self.check_range_int(new_node.value, symbol.zontype.name, span)
            
            if not error:
                node.assign_stmt.value = new_node
                symbol.value = new_node
                
        elif isinstance(new_node, FloatLiteral):
            error = False
            if symbol.zontype.num in [2, 7]:
                error = self.check_range_float(new_node.value, symbol.zontype.name, span)
            
            if not error:
                node.assign_stmt.value = new_node
                symbol.value = new_node
                
        elif isinstance(new_node, BoolLiteral):
            node.assign_stmt.value = new_node
            symbol.value = new_node if True else False
            
        else:
            node.assign_stmt.value = new_node
            symbol.value = new_node
        
    def visit_Assignment(self, node: AssignmentStmt, scope: Enviroment):
        span = node.span
        folded = self.evaluate_static_value(node.value, scope)
        new_node = self.transform_to_zonvalue(folded)
        new_node.span = span
        symbol = scope.get_symbol(node.name)
        
        if isinstance(new_node, IntLiteral):
            error = False
            if symbol.zontype.num in [1, 6]:
                error = self.check_range_int(new_node.value, symbol.zontype.name, span)
            
            if not error:
                node.assign_stmt.value = new_node
                symbol.value = new_node
                
        elif isinstance(new_node, FloatLiteral):
            error = False
            if symbol.zontype.num in [2, 7]:
                error = self.check_range_float(new_node.value, symbol.zontype.name, span)
            
            if not error:
                node.assign_stmt.value = new_node
                symbol.value = new_node
                
        elif isinstance(new_node, BoolLiteral):
            node.value = new_node
            symbol.value = new_node if True else False
            
        else:
            node.value = new_node
            symbol.value = new_node

    def evaluate_static_value(self, node, scope: Enviroment):
        match node:
            case BinaryExpr():
                left = self.evaluate_static_value(node.left, scope)
                right = self.evaluate_static_value(node.right, scope)

                if (isinstance(left, (int, float)) and not isinstance(left, bool)) and (isinstance(right, (int, float)) and not isinstance(right, bool)):
                    try:
                        match node.operator:
                            case Operator.ADD: return left + right
                            case Operator.SUB: return left - right
                            case Operator.MUL: return left * right
                            case Operator.DIV:
                                if isinstance(left, float):
                                    if right == 0:
                                        if left == 0:
                                            self.reporter.emit(
                                                ErrorCode.E5003, None, [node.span], [(node.span, "0.0 divided by 0.0 is mathematically undefined")]
                                            )
                                            
                                        else:
                                            inf = ""
                                            if left > 0:
                                                inf = "+Inf"
                                            elif left < 0:
                                                inf = "-Inf"
                                                
                                            self.reporter.emit(
                                                ErrorCode.E5002, { "inf" : inf }, [node.span], [(node.span, "this division results in an infinite value")]
                                            )
                                    
                                        return node
                                    return left / right

                                
                                    
                                if right == 0:
                                    self.reporter.emit(
                                        ErrorCode.E5001, None, [node.span], [(node.right.span, "constant folding evaluated this divisor to zero")]
                                    )
                                    return node
                                
                                return left / right
                            
                            case Operator.MOD:
                                if isinstance(left, float):
                                    if right == 0:
                                        self.reporter.emit(
                                            ErrorCode.E5001, None, [node.span], [(node.right.span, "constant folding evaluated this divisor to zero")]
                                        )
                                        return node
                                    return math.fmod(left, right)

                                else:
                                    if right == 0:
                                        self.reporter.emit(
                                            ErrorCode.E5001, None, [node.span], [(node.right.span, "constant folding evaluated this divisor to zero")]
                                        )
                                        return node
                                    return left % right
                                
                            case Operator.LT:
                                return left < right
                            
                            case Operator.GT:
                                return left > right
                            
                            case Operator.LE:
                                return left <= right
                            
                            case Operator.GE:
                                return left >= right
                            
                            case Operator.EQ:
                                return left == right
                            
                            case Operator.NE:
                                return left != right
                            
                            # recordar poner POW
                            

                    except OverflowError:
                        return float("inf")
                elif isinstance(left, bool) and isinstance(right, bool):
                    match node.operator:
                        case Operator.AND:
                            return left and right
                        
                        case Operator.OR:
                            return left or right
                        
                        case Operator.EQ:
                            return left == right
                        
                        case Operator.NE:
                            return left != right
                        
                node.left = self.transform_to_zonvalue(left)
                node.right = self.transform_to_zonvalue(right)
                return node

            case IntLiteral():
                if self.check_range_int(node.value, "int64", node.span):
                    return node
                return node.value
            
            case FloatLiteral():
                if math.isinf(node.value):
                    inf = ""
                    if node.value == math.inf:
                        inf = "inf"
                    else:
                        inf = "-inf"
                    
                    self.reporter.emit(
                        ErrorCode.E5005, 
                        { "target_type": "double", "max_val": "1.79e308", "inf" : inf }, 
                        [node.span], 
                        [(node.span, "value exceeds {target_type} range")]
                    )
                    return node
                
                if self.check_range_float(node.value, "double", node.span):
                    return node
                return node.value
            
            case BoolLiteral():
                return True if node.value else False

            case VariableExpr():
                symbol = scope.get_symbol(node.name)
                if not symbol.mutability:
                    return self.evaluate_static_value(symbol.value, scope)
                return node
            
            case UnaryExpr():
                value = self.evaluate_static_value(node.value, scope)
                if isinstance(value, (int, float)) and node.operator == Operator.NEG:
                    return -(value)
                
                elif isinstance(value, bool) and node.operator == Operator.NOT:
                    return (not value)
                
                node.value = self.transform_to_zonvalue(value)
                return node

            case BlockExpr():
                return self.visit_Program(node)
            
            case IfForm():
                self.visit_If(node, scope)
                self.visit_Program(node.if_branch.block)
                    
                if not node.elif_branches is None:
                    for branch in node.elif_branches:
                        self.visit_Program(branch.block)
                        
                if not node.else_branch is None:
                    self.visit_Program(node.else_branch.block)
                    
                return node
                
            case _:
                return node

    def transform_to_zonvalue(self, value):
        if isinstance(value, int) and not isinstance(value, bool): return IntLiteral(value)
        if isinstance(value, float): return FloatLiteral(value)
        if isinstance(value, bool): return BoolLiteral(1 if value else 0)
        else: return value
                
    def check_range_int(self, new_value, target_type, span) -> bool:
        min_val, max_val = RANGES.get(target_type, (0, 0))
        if new_value > max_val:
            magnitud = ""
            if target_type == "int32": magnitud = "~2.14 billion"
            if target_type == "int64": magnitud = "~9.22 quintillion"
            
            self.reporter.emit(
                ErrorCode.E5004, { "type_int" : target_type, "magnitud" : magnitud }, [span], [(span, "value is too large for type `{type_int}`")]
            )
            return True
        
        elif new_value < min_val:
            magnitud = ""
            if target_type == "int32": magnitud = "~ -2.14 billion"
            if target_type == "int64": magnitud = "~ -9.22 quintillion"
            
            self.reporter.emit(
                ErrorCode.E5005, { "type_int" : target_type, "magnitud" : magnitud }, [span], [(span, "value is too small for type `{type_int}`")]
            )
            return True
        return False
    
    def check_range_float(self, value, target_type, span) -> bool | None:
        fmt = 'f' if target_type == "float" else 'd'
        max_val = "3.40e38" if target_type == "float" else "1.79e308"
        
        try:
            packed = struct.pack(fmt, value)
            unpacked_val = struct.unpack(fmt, packed)[0]
            
            if math.isinf(unpacked_val) and not math.isinf(value):
                inf = ""
                if unpacked_val > 0:
                    inf = "inf"
                else:
                    inf = "-inf"
                
                self.reporter.emit(
                    ErrorCode.E5005, 
                    { "target_type": target_type, "max_val": max_val, "inf" : inf }, 
                    [span], 
                    [(span, f"value exceeds {target_type} range")]
                )
                return True
            
            elif unpacked_val == 0.0 and value != 0.0:
                min_val = "1.18e-38" if target_type == "float" else "2.23e-308"

                self.reporter.emit(
                    ErrorCode.W5001,
                    { "target_type": target_type, "min_val": min_val },
                    [span],
                    [(span, f"value exceeds {target_type} range minimal")]
                )
    
                return False
            
        except (OverflowError, ValueError):
            return True
            
        return False
    
    def visit_Program(self, node: Program | BlockExpr):
        scope: Enviroment = node.scope
        scope.values.clear()
        
        for stmt in node.stmts:
            if isinstance(stmt, DeclarationStmt):
                symbol = Symbol(stmt.mut, stmt.type, True, stmt.span)
                scope.define(stmt.name, symbol)
                
            elif isinstance(stmt, AssignmentStmt):
                self.visit_Assignment(stmt, scope)
            
            elif isinstance(stmt, InitializationStmt):
                self.visit_Initialization(stmt, scope)
            
            elif isinstance(stmt, BlockExpr):
                self.visit_Program(stmt)
                
            elif isinstance(stmt, IfForm):
                self.visit_If(stmt, scope)
                self.visit_Program(stmt.if_branch.block)
                if not stmt.elif_branches is None:
                    for branch in stmt.elif_branches:
                        self.visit_Program(branch.block)
                        
                if not stmt.else_branch is None:
                    self.visit_Program(stmt.else_branch.block)
                
            elif isinstance(stmt, GiveStmt):
                value = self.evaluate_static_value(stmt.value, scope)
                value_new = self.transform_to_zonvalue(value)
                stmt.value = value_new
                return value
            
            elif isinstance(stmt, CallFunc):
                if stmt.name == "print":
                    self.visit_Print(stmt, scope)
            
            else:
                return None
                
    
            