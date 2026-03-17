from zonc.ast import *
from zonc.zonc_errors import DiagnosticEngine
from zonc.enviroment import Enviroment, Symbol
from zonc.zonc_errors import ErrorCode
from zonc.location_file import Span, FileMap
    
# TODO: seguir con block_expr
class Semantic:
    def __init__(self, diag: DiagnosticEngine, file_map: FileMap) -> None:
        self.diag = diag
        self.file_map = file_map
        
           
    def check_ast(self, ast: Node):
        scope: Enviroment = ast.scope
        for node in ast.stmts:
            if isinstance(node, DeclarationStmt):
                scope.define(
                    node.name,
                    Symbol(
                        node.mut,
                        node.type,
                        True
                    )
                )
                
            elif isinstance(node, AssignmentStmt):
                value_type = self.infer_expr(node.value, scope)
                
                if value_type == ZonType.UNKNOWN:
                    continue
                
                symbol = scope.get_symbol(node.name)
                
                if symbol is None:
                    self.diag.emit(
                        ErrorCode.E3001,
                        { "name" : node.name },
                        node.span,
                        (node.span_name, "does not exist in this scope")
                    )
                    continue
                
                if not symbol.mutability and not symbol.is_empty:
                    self.diag.emit(
                        ErrorCode.E3005,
                        { "name" : node.name },
                        node.span,
                        (node.span_name, "is inmutable, it was already assigned a value")
                    )
                    continue
                
                if symbol.zontype == ZonType.UNKNOWN:
                    symbol.zontype = value_type
                    
                elif symbol.zontype != value_type:
                    if isinstance(node.value, BlockExpr):
                        self.diag.emit(
                            ErrorCode.E3006,
                            { "name" : node.name,
                            "expected_type" : symbol.zontype.name,
                            "found_type" : value_type.name},
                            Span(node.span.start, node.value.stmts[node.value.give_address].span.end, self.file_map),
                            (node.value.stmts[node.value.give_address].value.span, "this expression returns '{found_type}', but '{name}' expects '{expected_type}'")
                        )
                    else:
                        self.diag.emit(
                            ErrorCode.E3006,
                            { "name" : node.name,
                            "expected_type" : symbol.zontype.name,
                            "found_type" : value_type.name},
                            node.span,
                            (node.value.span, "this expression returns '{found_type}', but '{name}' expects '{expected_type}'")
                        )
                    continue
            
                if symbol.is_empty:
                    symbol.is_empty = False  
            
            elif isinstance(node, BlockExpr):
                if not(node.give_address is None):
                    unreachable = len(node.stmts) - node.give_address - 1
                    
                    if unreachable == 1:
                        self.diag.emit(
                            ErrorCode.W3001,
                            None,
                            Span(node.span.start, node.stmts[node.give_address].span.end, self.file_map),
                            (node.stmts[node.give_address].span, "1 statement below this will never execute")
                        )
                        
                    elif unreachable > 1:
                        self.diag.emit(
                            ErrorCode.W3001,
                            None,
                            Span(node.span.start, node.stmts[node.give_address].span.end, self.file_map),
                            (node.stmts[node.give_address].span, f"{unreachable} statements below this will never execute")
                        )
                
                self.check_ast(node)
                
            elif isinstance(node, GiveStmt):
                break
                
    
    
    def check_operands_type(
        self,
        operands_type: tuple[tuple[ZonType, Span], tuple[ZonType, Span]] | tuple[tuple[ZonType, Span]],
        return_type: ZonType,
        equal: bool,
        operator: str,
        *zontypes,
    ):    
    
        len_types = len(zontypes)
    
        for i in range(len(operands_type)):
            no_match = 0
            
            for j in range(len_types):
                if operands_type[i][0] != zontypes[j]:
                    no_match += 1
            
            if no_match == len_types:
                valid_types = ""
                
                for j in range(len_types):
                    if j < len_types-1:
                        if j == (len_types-2):
                            valid_types += f"{zontypes[j].name} or "
                        else:
                            valid_types += f"{zontypes[j].name}, "
                    
                    elif j == len_types-1:
                        valid_types += f"{zontypes[j].name}"
                
                self.diag.emit(
                    ErrorCode.E3003,
                    { "operator" : operator, 
                        "valid_types" : valid_types,
                        "found_type" : operands_type[i][0].name},
                    operands_type[i][1],
                    (operands_type[i][1], "this operand is `{found_type}`, but `{operator}` expects {valid_types}")
                )
                return ZonType.UNKNOWN
                
        if equal:
            if operands_type[0][0] != operands_type[1][0]:
                self.diag.emit(
                    ErrorCode.E3004,
                    { "operator" : operator,
                      "right_type" : operands_type[1][0].name,
                      "left_type" :  operands_type[0][0].name},
                    operands_type[1][1],
                    (operands_type[1][1], "this is `{right_type}`, but `{operator}` expects `{left_type}` to match the left operand")
                )
                return ZonType.UNKNOWN
            
        return return_type
                
        
    def infer_expr(self, expr: NodeExpr, scope: Enviroment) -> ZonType:
        if isinstance(expr, IntLiteral):
            return ZonType.INT
        
        elif isinstance(expr, FloatLiteral):
            return ZonType.FLOAT
        
        elif isinstance(expr, BoolLiteral):
            return ZonType.BOOL
        
        elif isinstance(expr, StringLiteral):
            return ZonType.STRING
        
        elif isinstance(expr, BinaryExpr):
            op = expr.operator
            left_type = self.infer_expr(expr.left, scope)
            right_type = self.infer_expr(expr.right, scope)
            
            if left_type == ZonType.UNKNOWN or right_type == ZonType.UNKNOWN:
                return ZonType.UNKNOWN
            
            if op == Operator.ADD or op == Operator.SUB or op == Operator.MUL or op == Operator.POW or op == Operator.MOD or op == Operator.DIV:
                op_str: str
                match op:
                    case Operator.ADD: op_str = '+'
                    case Operator.SUB: op_str = '-'
                    case Operator.MUL: op_str = '*'
                    case Operator.DIV: op_str = '/'
                    case Operator.MOD: op_str = '%'
                    case Operator.POW: op_str = "**"
                
                
                return self.check_operands_type(
                    ((left_type, expr.left.span), (right_type, expr.right.span)),
                    left_type,
                    True,
                    op_str,
                    ZonType.INT, ZonType.FLOAT
                )
            
            elif op == Operator.LT or op == Operator.GT or op == Operator.LE or op == Operator.GE:
                op_str: str
                match op:
                    case Operator.LT: op_str = '<'
                    case Operator.GT: op_str = '>'
                    case Operator.LE: op_str = '<='
                    case Operator.GE: op_str = '>='
                
                return self.check_operands_type(
                    ((left_type, expr.left.span), (right_type, expr.right.span)),
                    left_type,
                    True,
                    op_str,
                    ZonType.INT, ZonType.FLOAT
                )
            
            elif op == Operator.AND or op == Operator.OR:
                op_str: str
                match op:
                    case Operator.AND: op_str = 'and/&&'
                    case Operator.OR: op_str = 'or/||'
                
                
                return self.check_operands_type(
                    ((left_type, expr.left.span), (right_type, expr.right.span)),
                    left_type,
                    False,
                    op_str,
                    ZonType.BOOL
                )
            
            elif op == Operator.EQ or op == Operator.NE:
                op_str: str
                match op:
                    case Operator.EQ: op_str = '=='
                    case Operator.NE: op_str = '!='
                
                
                return self.check_operands_type(
                    ((left_type, expr.left.span), (right_type, expr.right.span)),
                    left_type,
                    True,
                    op_str,
                    ZonType.INT, ZonType.FLOAT, ZonType.BOOL, ZonType.STRING
                )
                
        elif isinstance(expr, UnaryExpr):
            op = expr.operator
            value_type = self.infer_expr(expr.value, scope)
            
            if value_type == ZonType.UNKNOWN:
                return ZonType.UNKNOWN
            
            if op == Operator.NEG:
                return self.check_operands_type(
                    ((value_type, expr.value.span),),
                    value_type,
                    False,
                    '-',
                    ZonType.INT, ZonType.FLOAT
                )
            
            else:
                return self.check_operands_type(
                    ((value_type, expr.value.span),),
                    value_type,
                    False,
                    'not/!',
                    ZonType.BOOL
                )
        
        elif isinstance(expr, VariableExpr):
            symbol = scope.get_symbol(expr.name)
            
            if symbol is None:
                self.diag.emit(
                    ErrorCode.E3001,
                    { "name" : expr.name },
                    expr.span,
                    (expr.span, "does not exist in this scope")
                )
                return ZonType.UNKNOWN
            
            elif symbol.is_empty:
                self.diag.emit(
                    ErrorCode.E3002,
                    { "name" : expr.name },
                    expr.span,
                    (expr.span, "has no value at this point")
                )
                return ZonType.UNKNOWN
            
            return symbol.zontype
        
        elif isinstance(expr, BlockExpr):
            unreacheable = len(expr.stmts) - expr.give_address - 1
            
            if unreacheable == 1:
                self.diag.emit(
                    ErrorCode.W3001,
                    None,
                    Span(expr.span.start, expr.stmts[expr.give_address].span.end, self.file_map),
                    (expr.stmts[expr.give_address].span, "1 statement below this will never execute"),
                )
                
            elif unreacheable > 1:
                self.diag.emit(
                    ErrorCode.W3001,
                    None,
                    Span(expr.span.start, expr.stmts[expr.give_address].span.end, self.file_map),
                    (expr.stmts[expr.give_address].span, f"{unreacheable} statements below this will never execute"),
                )
                
            self.check_ast(expr)
                
            return self.infer_expr(expr.stmts[expr.give_address].value, expr.scope)
                

            
            
        
        
 
        
        
    
            
        