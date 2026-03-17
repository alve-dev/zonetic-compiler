from zonc.ast import *
from zonc.zonc_errors import DiagnosticEngine
from zonc.enviroment import Enviroment

class Interpreter:
    def __init__(self, root_node: Program, reporter: DiagnosticEngine):
        self.root_node = root_node
        self.reporter = reporter


    def stop(self):
        raise Exception


    def interpret_main(self):
        statements = self.root_node.statements
        scope = self.root_node.scope
        for statement in statements:
            if isinstance(statement, DeclarationNode):
                self.visit_declar(statement, scope)
            elif isinstance(statement, AssignmentNode):
                self.visit_assing(statement, scope)
            elif isinstance(statement, CallNode):
                self.visit_call_node(statement, scope)
            elif isinstance(statement, IfNode):
                self.visit_if_node(statement)
            elif isinstance(statement, WhileNode):
                self.visit_while_node(statement)
    
    
    def interpretet_block(self, block_node: BlockExpr):
        statements = block_node.statements
        scope: Enviroment = block_node.scope
        
        for statement in statements:
            if isinstance(statement, DeclarationNode):
                self.visit_declar(statement, scope)
            elif isinstance(statement, AssignmentNode):
                self.visit_assing(statement, scope)
            elif isinstance(statement, CallNode):
                self.visit_call_node(statement, scope)
            elif isinstance(statement, IfNode):
                state = self.visit_if_node(statement)
                
                if state == "continue":
                    return "continue"
                elif state == "break":
                    return "break"
                elif state == "pass":
                    continue
                
            elif isinstance(statement, BreakStatement):
                return "break"
            elif isinstance(statement, ContinueStatement):
                return "continue"
            elif isinstance(statement, WhileNode):
                self.visit_while_node(statement)
        
        return "pass"
       
                   
    def visit_literal(self, literal_node: LiteralNode):
        return literal_node.value
   
           
    def visit_unary(self, unary_node: UnaryExpr, scope: Enviroment):
        sign_unary = unary_node.operator
        value = self.visit_node(unary_node.node, scope)
            
        if sign_unary == '-':
            return -value
        elif sign_unary == '+':
            return +value
    
    
    def visit_comparison_operation(self, comparison_op_node: BinaryExpr, scope: Enviroment):
        left = self.visit_node(comparison_op_node.left, scope)
        operator = comparison_op_node.operator
        right = self.visit_node(comparison_op_node.right, scope)
        
        if operator == '<':
            return left < right
        elif operator == '>':
            return left > right
        elif operator == '<=':
            return left <= right
        elif operator == '>=':
            return left >= right
        elif operator == '==':
            return left == right
        elif operator == '!=':
            return left != right
            
               
    def visit_boolean_operation(self, boolean_op_node: BinaryExpr, scope: Enviroment):
        left = self.visit_node(boolean_op_node.left, scope)
        operator = boolean_op_node.operator
        
        # short-circuit
        if operator == "and" and left == False:
            return False
        elif operator == "or" and left == True:
            return True 
        
        right = self.visit_node(boolean_op_node.right, scope)
        
        if operator == "and":
            return left and right
        if operator == "or":
            return left or right


    def visit_not_boolean_operator(self, not_boolean_operator: UnaryExpr, scope: Enviroment):
        value_bool = self.visit_node(not_boolean_operator.node, scope)
        
        if isinstance(value_bool, bool):
            return not value_bool
        else:
            self.reporter.add_error(
                f"[BooleanError] You cannot operate on a non-bool value with the boolean operator not"
            )
            self.stop()

            
    def visit_binary_operation(self, binary_op_node: BinaryExpr, scope: Enviroment):
        line_operation = binary_op_node.left.line
        column_operation = binary_op_node.left.column
        left = self.visit_node(binary_op_node.left, scope)
        operator = binary_op_node.operator
        right = self.visit_node(binary_op_node.right, scope)
        
        if operator == '+':
            return left + right
        
        elif operator == '-':
            return left - right
        
        elif operator == '*':
            return left * right
        
        elif operator == '/':
            if right == 0:
                self.reporter.add_error(
                    f"[ZeroDivisionError][line: {line_operation}, col: {column_operation}] You cannot divide a number by zero"
                )
                self.stop()

            else:
                if isinstance(left, int) and isinstance(right, int):
                    return left // right
            
                return left / right
            
        elif operator == '%':
            if right == 0:
                self.reporter.add_error(
                    f"[ZeroDivisionError][line: {line_operation}, col: {column_operation}] You cannot find the modulus of a number divided by zero"
                )
                self.stop()
                
            else:
                return left % right
            
        elif operator == "**":
            return left ** right


    def visit_variable(self, var_node: VariableExpr, scope: Enviroment):
        value = scope.get(var_node.name)
        
        if not value is None:
            return value
    
    
    def visit_declar(self, decl_node: DeclarationStmt, scope: Enviroment):
        value = self.visit_node(decl_node.value, scope)
        symbol = Symbol(value, decl_node.type, decl_node.mutable)
        scope.add_symbol(symbol, decl_node.name)
        
    def visit_assing(self, assing_node: AssignmentStmt, scope: Enviroment):
        value = self.visit_node(assing_node.value, scope)
        scope.assign(assing_node.name, value)
  
    def visit_if_node(self, if_node: IfForm):
        len_branches = len(if_node.branches)
        for body in range(len_branches):
            condition = if_node.branches[body][0]
            scope = if_node.branches[body][1].scope
             
            bool_conditional = self.visit_node(condition, scope)
                
            if bool_conditional:
                state = self.interpretet_block(if_node.branches[body][1])
                return state
            
        if isinstance(if_node.else_node, ElseNode):
            state = self.interpretet_block(if_node.else_node.block)
            return state


    def visit_while_node(self, while_node: WhileForm):
        block = while_node.block
        while self.visit_node(while_node.condition, while_node.block.scope):
            state = self.interpretet_block(block)

            if state == "break":
                break
            elif state == "continue":
                continue

    # Builtin Functions temporals
    def builtin_write(args) -> None:
        values = []
        for arg in args:
            values.append(arg)
        
        print(*values, end="")
        return None
    
    
    # Builtin Functions temporals
    def builtin_writeline(args) -> None:
        values = []
        for arg in args:
            values.append(arg)
        
        print(*values)
        return None
    
    
    def builtin_read_int(args) -> int:
        values = []
        for arg in args:
            values.append(arg)
            
        input_int = input(*values)
        
        while True:
            try:
                input_int = int(input_int)
                break
            except ValueError:
                input_int = input(*values)
         
        return input_int
    
    
    def builtin_read_float(args) -> float:
        values = []
        for arg in args:
            values.append(arg)
            
        input_float = input(*values)
        
        while True:
            try:
                input_float = float(input_float)
                break
            except ValueError:
                input_float = input(*values)
         
        return input_float
        
        
    def builtin_read_string(args) -> str:
        values = []
        for arg in args:
            values.append(arg)
            
        input_string = input(*values)
        return input_string
    
    
    def builtin_read_bool(args) -> bool:
        values = []
        for arg in args:
            values.append(arg)
            
        input_string = input(values[0])
        
        while True:
            if input_string == values[1]:
                return True
            elif input_string == values[2]:
                return False
            else:
                input_string = input(values[0])  
        
                  
    BUILTINS = {
        "writeline":builtin_writeline,
        "write":builtin_write,
        "readInt":builtin_read_int,
        "readFloat":builtin_read_float,
        "readString":builtin_read_string,
        "readBool":builtin_read_bool,
    }


    def visit_call_node(self, call_node: Node, scope: Enviroment):
        args = []
            
        for arg in call_node.args:
            value_arg = self.visit_node(arg, scope)
            args.append(value_arg)
                
        return self.BUILTINS[call_node.calle](args)


    def visit_node(self, node: Node, scope):
        if isinstance(node, CallNode):
            return self.visit_call_node(node, scope)
        
        if isinstance(node, VariableNode):
            return self.visit_variable(node, scope)
        
        elif isinstance(node, BinaryOpNode):
            return self.visit_binary_operation(node, scope)
        
        elif isinstance(node, UnaryNode):
            return self.visit_unary(node, scope)
        
        elif isinstance(node, NotBooleanNode):
            return self.visit_not_boolean_operator(node, scope)
        
        elif isinstance(node, ComparisonOpNode):
            return self.visit_comparison_operation(node, scope)
        
        elif isinstance(node, BooleanOpNode):
            return self.visit_boolean_operation(node, scope)
        
        elif isinstance(node, IntNode):
            return self.visit_literal(node)
        
        elif isinstance(node, FloatNode):
            return self.visit_literal(node)
        
        elif isinstance(node, BoolNode):
            return self.visit_literal(node)
        
        elif isinstance(node, StringNode):
            return self.visit_literal(node)
        