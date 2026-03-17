from zonc.scanner import *
from zonc.ast import *
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from zonc.enviroment import Enviroment
from zonc.location_file import Span, FileMap
from typing import List, Union



class Parser:
    COMPOUND_TO_OPERATOR = {
        TokenType.OPERATOR_PLUS_ASSIGN : Operator.ADD,
        TokenType.OPERATOR_MINUS_ASSIGN : Operator.SUB,
        TokenType.OPERATOR_MULT_ASSIGN : Operator.MUL,
        TokenType.OPERATOR_DIV_ASSIGN : Operator.DIV,
        TokenType.OPERATOR_MOD_ASSIGN : Operator.MOD,
        TokenType.OPERATOR_POW_ASSIGN : Operator.POW
    }
    
    TOKEN_TO_OPERATOR = {
        TokenType.OPERATOR_PLUS : Operator.ADD,
        TokenType.OPERATOR_MINUS : Operator.SUB,
        TokenType.OPERATOR_MULT : Operator.MUL,
        TokenType.OPERATOR_DIV : Operator.DIV,
        TokenType.OPERATOR_MOD : Operator.MOD,
        TokenType.OPERATOR_GREATER : Operator.GT,
        TokenType.OPERATOR_GREATER_EQUAL : Operator.GE,
        TokenType.OPERATOR_LESS : Operator.LT,
        TokenType.OPERATOR_LESS_EQUAL : Operator.LE,
        TokenType.OPERATOR_EQUAL : Operator.EQ,
        TokenType.OPERATOR_NOT_EQUAL : Operator.NE
    }
    
    
    def __init__(self, tokens: ListTokens, diag: DiagnosticEngine, file_map: FileMap) -> None:
        self.tokens = tokens
        self.position = 0
        self.length_list = self.tokens._len()
        self.diag = diag
        self.file_map = file_map


    def at_end(self) -> bool:
        return self.tokens._peek(self.position)._type == TokenType.EOF


    def advance(self) -> bool:
        if self.at_end():
            return False
        
        self.position += 1
        return True
    
    
    def synchronize(self, block: bool):
        while not self.at_end():
        
            if self.match_token_type(
                TokenType.KEYWORD_MUT,
                TokenType.KEYWORD_INMUT,
                TokenType.KEYWORD_IF,
                TokenType.KEYWORD_WHILE,
                TokenType.KEYWORD_INFINITY,
                TokenType.LITERAL_IDENT
            ):
                return
            
            elif block and self.check(TokenType.RBRACE):
                return
            
            else:
                self.advance()
    
    
    #Seguir mañana y arreglar los comentarios de errores en las lines e columna
    def check(self, type: TokenType) -> bool:
        if self.at_end(): 
            return False
    
        return self.tokens._peek(self.position)._type == type


    def match_token_type(self, *types) -> bool:
        for type in types:
            if self.check(type):
                return True
        
        return False
    
    
    def parse_program(self) -> Program:
        statements: list[Node] = []
        scope = Enviroment()
        
        while True:
            if self.check(TokenType.SEMICOLON):
                self.advance()
                continue
                
            if self.at_end():
                break
            
            node = self.parse_statement(scope, False)
            
            if isinstance(node, list):
                for statement in node:
                    statements.append(statement)
            elif isinstance(node, ErrorNode):
                continue
            else:
                statements.append(node)
            
        return Program(statements, scope)
    
    
    def parse_statement(self, scope: Enviroment, block: bool) -> Node:
        # Declaration Statement
        if self.match_token_type(
            TokenType.KEYWORD_MUT,
            TokenType.KEYWORD_INMUT
        ):
            mut: bool
            
            if self.check(TokenType.KEYWORD_MUT):
                mut = True
            else:
                mut = False
                
            self.advance()
            return self.parse_declaration(
                mut,
                scope,
                self.tokens._peek(self.position)._span.start,
                block
            )
        
        # Assignment Statement
        elif self.check(TokenType.LITERAL_IDENT):
            token = self.tokens._peek(self.position)
            self.advance()
            
            return self.parse_assignment(
                scope,
                token._value,
                token._span,
                token._span.start,
                block
            )
            
        # Block Expression
        elif self.check(TokenType.LBRACE):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_block_expr(False, token._span.start, scope, block)
        
        # Give Statement
        elif self.check(TokenType.KEYWORD_GIVE):
            token = self.tokens._peek(self.position)
            self.advance()
            value = self.expression(scope, block)
            return GiveStmt(
                value,
                Span(token._span.start, value.span.end, self.file_map)
            )
            
        elif self.check(TokenType.KEYWORD_IF):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_if_form(scope, False, token._span.start, block)
        
        elif self.match_token_type(
            TokenType.KEYWORD_ELIF,
            TokenType.KEYWORD_ELSE
        ):
            token_err = self.tokens._peek(self.position)
            
            self.diag.emit(
                ErrorCode.E2011,
                { "keyword" : token_err._value },
                token_err._span,
                (token_err._span, "`if` was expected before this `{keyword}`")
            )
            
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
        
        elif self.check(TokenType.KEYWORD_WHILE):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_while_form(scope, token._span.start, False, block)
        
        elif self.check(TokenType.KEYWORD_INFINITY):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_while_form(scope, token._span.start, True, block)
        
        elif self.check(TokenType.KEYWORD_BREAK):
            token = self.tokens._peek(self.position)
            self.advance()
            return BreakStmt(token._span)
        
        elif self.check(TokenType.KEYWORD_CONTINUE):
            token = self.tokens._peek(self.position)
            self.advance()
            return ContinueStmt(token._span)
        
        elif self.check(TokenType.KEYWORD_PRINT):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_print_stmt(scope, token._span.start, block)

        else:
            token_err = self.tokens._peek(self.position)
            
            self.diag.emit(
                ErrorCode.E2010,
                { "token" : token_err._value },
                token_err._span,
                (token_err._span, "this is not a valid way to start a statement")
            )
            
            self.synchronize(block)
            
            return ErrorNode(Span(0, 0, self.file_map))
        
        
    def parse_declaration(self, mutable: bool, scope: Enviroment, start: int, block: bool) -> List[Union[DeclarationStmt, AssignmentStmt]]:
        node = self.parse_single_declaration(mutable, scope, start, block)
        declarations = []
        
        if isinstance(node, list):
            if not isinstance(node[0], ErrorNode):
                return node
            if not isinstance(node[1], ErrorNode):
                return node
            
            declarations.append(node[0])
            declarations.append(node[1])
            
        elif isinstance(node, ErrorNode):
            return node
        else:
            declarations.append(node)
        
        #Posible multi-Declaration sino single-declaration
        if self.check(TokenType.COMMA):
            self.advance()
            
            for declaration in self.parse_declaration(mutable, scope, start):
                declarations.append(declaration)
            
            return declarations
                
        elif self.check(TokenType.SEMICOLON):
            return declarations
        
        else:
            token = self.tokens._peek(self.position)
            
            self.diag.emit(
                ErrorCode.E2004,
                { "token" : token._value },
                Span(start, token._span.end, self.file_map),
                (token._span, "expected `;` or `,` here to end or continue the declaration")
            )
            
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
        
    
    def parse_single_declaration(self, mutable: bool, scope: Enviroment, start: int, block: bool) -> DeclarationStmt | List[Union[DeclarationStmt, AssignmentStmt]]:
        name_mut = "mutable" if mutable else "inmutable"
        ident = self.tokens._peek(self.position)
        
        if self.check(TokenType.LITERAL_IDENT):
            self.advance()
            
            var_name = ident._value
            var_type: ZonType
                
            if self.check(TokenType.COLON):
                self.advance()
                zon_type = self.tokens._peek(self.position)
                current_span = zon_type._span
                       
                match zon_type._type:
                    case TokenType.KEYWORD_INT: var_type = ZonType.INT
                    case TokenType.KEYWORD_FLOAT: var_type = ZonType.FLOAT
                    case TokenType.KEYWORD_BOOL: var_type = ZonType.BOOL
                    case TokenType.KEYWORD_STRING: var_type = ZonType.STRING
                    case _:
                        self.diag.emit(
                            ErrorCode.E2002,
                            { "type" : zon_type._value },
                            Span(start, current_span.end, self.file_map),
                            (current_span, "is not a valid type in Zonetic")
                        )
                        
                        self.synchronize(block)
                        return ErrorNode(Span(0, 0, self.file_map))
                
                end_offset = current_span.end
                self.advance()
            
            else:
                var_type = ZonType.UNKNOWN
                end_offset = self.tokens._peek(self.position)._span.end
            
            if self.check(TokenType.OPERATOR_ASSIGN):
                return [
                    DeclarationStmt(
                        var_name,
                        mutable, 
                        var_type,
                        Span(start, end_offset, self.file_map)
                    ),
                    
                    self.parse_assignment(scope, var_name, ident._span, start, block)
                ]
            
            else:
                return DeclarationStmt(var_name, mutable, var_type, Span(start, end_offset, self.file_map))
        
        else:
            self.diag.emit(
                ErrorCode.E2001,
                { "name_mut" : name_mut },
                Span(start, ident._span.end, self.file_map),
                (ident._span, "an identifier was expected here"),
            )
            
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
        
            
    def parse_assignment(self, scope: Enviroment, name: str, span_name: Span, start: int, block: bool) -> AssignmentStmt:
        token = self.tokens._peek(self.position)
        
        self.advance()
        
        if token._type == TokenType.OPERATOR_ASSIGN:
            expr = self.expression(scope, block)
            end_offset = expr.span.end
        
            return AssignmentStmt(
                name,
                expr,
                Span(start, end_offset, self.file_map),
                span_name
            )
        elif token._type in self.COMPOUND_TO_OPERATOR:
            var = VariableExpr(
                name,
                Span(token._span.start, token._span.end, self.file_map)
            )
            
            right_expr = self.expression(scope, block)
            
            expr = BinaryExpr(
                var,
                self.COMPOUND_TO_OPERATOR[token._type],
                right_expr,
                Span(var.span.start, right_expr.span.end, self.file_map)
                
            )
            
            return AssignmentStmt(
                name,
                expr,
                Span(start, expr.span.end, self.file_map),
                span_name
            )
        else:
            self.diag.emit(
                ErrorCode.E2006,
                { "token" : token._value ,
                  "name" : name },
                Span(start, token._span.end, self.file_map),
                (token._span, "expected an assignment operator here")
            )
            
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
    
    
    def parse_block_expr(self, expects_value: bool, start: int, scope_back: Enviroment, block: bool) -> BlockExpr:
        statements: list[Node] = []
        give_value: GiveStmt
        is_value_give = False
        end: int
        
        scope = Enviroment(scope_back)
        
        while True:
            if self.check(TokenType.SEMICOLON):
                self.advance()
                continue
            
            if self.at_end():
                token_eof = self.tokens._peek(self.position)
                
                self.diag.emit(
                    ErrorCode.E2008,
                    {"aux_l": '}',
                     "aux_r" : '{'},
                    Span(start, token_eof._span.end-1, self.file_map),
                    (Span(token_eof._span.end-2, token_eof._span.end-1, self.file_map), "`{aux_l}` was expected here to close the block")
                )
                
                return ErrorNode(Span(0, 0, self.file_map))
            
            if self.check(TokenType.RBRACE):
                end = self.tokens._peek(self.position)._span.end
                self.advance()
                break
            
            node = self.parse_statement(scope, True)
            
            if isinstance(node, list):
                for statement in node:
                    statements.append(statement)
            elif isinstance(node, ErrorNode):
                continue
            elif isinstance(node, GiveStmt):
                give_value = node
                statements.append(node)
                is_value_give = True
            else:
                statements.append(node)
        
        span_block = Span(start, end, self.file_map)
        
        if is_value_give:
            if not expects_value:
                self.diag.emit(
                    ErrorCode.W2001,
                    None,
                    Span(start, give_value.span.end, self.file_map),
                    (give_value.span, "this `give` is unreachable, no value is expected from this block")
                )
            
            return BlockExpr(
                statements,
                statements.index(give_value),
                scope,
                span_block,
            )
            
        else:
            if expects_value:
                #error de retorno esperado, aqui si retorno un error node y syncronize
                end_stmt = statements[-1]
                self.diag.emit(
                    ErrorCode.E2007,
                    None,
                    Span(start, end_stmt.span.end, self.file_map),
                    (end_stmt.span, "`give` with a value was expected here")
                )
                
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
        
        return BlockExpr(
            statements,
            None,
            scope,
            span_block,
        )   
                
        
    def parse_if_form(self, scope_back: Enviroment, expects_value: bool, start: int, block: bool) -> IfForm:
        elif_branches = []
        else_branch = None
        
        cond = self.expression(scope_back, block)
        
        token = self.tokens._peek(self.position)
        
        if token._type != TokenType.LBRACE:
            
            self.diag.emit(
                ErrorCode.E2009,
                { "aux_r" : '{',
                  "token": token._value},
                Span(start, token._span.end, self.file_map),
                (token._span, "`{aux_r}` was expected here to open the branch block")
            )
            
            self.synchronize(block)
            
            return ErrorNode(Span(0, 0, self.file_map))
        
        self.advance()
        block_expr = self.parse_block_expr(expects_value, token._span.start, scope_back, block)
        
        if_branch = IfBranch(
            cond,
            Span(start, block_expr.span.end, self.file_map),
            block_expr
        )
        
        while True:
            if self.check(TokenType.KEYWORD_ELIF):
                token_elif = self.tokens._peek(self.position)
                self.advance()
                cond = self.expression(scope_back, block)
                
                token = self.tokens._peek(self.position)
        
                if token._type != TokenType.LBRACE:
                    token_err = self.tokens._peek(self.position)
            
                    self.diag.emit(
                        ErrorCode.E2009,
                        { "aux_r" : '{',
                        "token": token_err._value},
                        Span(start, token_err._span.end, self.file_map),
                        (token_err._span, "`{aux_r}` was expected here to open the branch block")
                    )
                    
                    self.synchronize(block)
                    
                    return ErrorNode(Span(0, 0, self.file_map))
                
                self.advance()
                block_expr = self.parse_block_expr(expects_value, token._span.start, scope_back, block)
                
                elif_branches.append(
                    IfBranch(
                        cond,
                        Span(token_elif._span.start, block_expr.span.end, self.file_map),
                        block_expr
                    )
                )
            else:
                break
                
        if self.check(TokenType.KEYWORD_ELSE):
            token_else = self.tokens._peek(self.position)
            self.advance()
            
            token = self.tokens._peek(self.position)
            
            if token._type != TokenType.LBRACE:
                token_err = self.tokens._peek(self.position)
            
                self.diag.emit(
                    ErrorCode.E2009,
                    { "aux_r" : '{',
                    "token": token_err._value},
                    Span(start, token_err._span.end, self.file_map),
                    (token_err._span, "`{aux_r}` was expected here to open the branch block")
                )
                
                self.synchronize(block)
                
                return ErrorNode(Span(0, 0, self.file_map))
            
            self.advance()
            block_expr = self.parse_block_expr(expects_value, token._span.start, scope_back, block)
            
            else_branch = IfBranch(
                BoolLiteral(1, Span(0, 0, self.file_map)),
                Span(token_else._span.start, block_expr.span.end, self.file_map),
                block_expr
            )
            
        span_if_form: Span
        if not(else_branch is None):
            span_if_form = Span(start, else_branch.span.end, self.file_map)
        elif len(elif_branches) > 0:
            span_if_form = Span(start, elif_branches[-1].span.end, self.file_map)
        else:
            span_if_form = Span(start, if_branch.span.end, self.file_map)
        
        return IfForm(
            if_branch,
            elif_branches,
            else_branch,
            span_if_form
        )
    
    
    def parse_while_form(self, scope_back: Enviroment, start: int, infinity: bool, block: bool) -> WhileForm:
        cond: Node
        
        if infinity:
            cond = BoolLiteral(1, Span(0, 0, self.file_map))
        else:
            cond = self.expression(scope_back, block)
        
        token = self.tokens._peek(self.position)
        
        if token._type != TokenType.LBRACE: 
            self.diag.emit(
                ErrorCode.E2009,
                { "aux_r" : '{',
                  "token": token._value},
                Span(start, token._span.end, self.file_map),
                (token._span, "`{aux_r}` was expected here to open the block")
            )
            
            self.synchronize(block)
            
            return ErrorNode(Span(0, 0, self.file_map))
        
        self.advance()
        block_expr = self.parse_block_expr(False, token._span.start, scope_back, block)
        
        return WhileForm(
            cond,
            block_expr,
            Span(start, block_expr.span.end, self.file_map)
        )
        
    
    def parse_print_stmt(self, scope: Enviroment, start: int, block: bool) -> PrintStmt:
        args = []
        while True:
            args.append(self.expression(scope, block))
            
            if self.check(TokenType.COMMA):
                self.advance()
                continue
            elif self.check(TokenType.SEMICOLON):
                return PrintStmt(
                    args,
                    Span(start, args[-1].span.end, self.file_map)
                )
            
        
    def expression(self, scope: Enviroment, block: bool) -> Node:
        return self.logic_or_expr(scope, block)
    

    def logic_or_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.logic_and_expr(scope, block)
        
        start = node.span.start
        
        while self.check(TokenType.GATE_OR):
            self.advance()
            
            left = self.logic_and_expr(scope, block)
            
            end = left.span.end
            
            node = BinaryExpr(
                node,
                Operator.OR,
                left,
                Span(start, end, self.file_map)
            )
        
        return node
    
    
    def logic_and_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.logic_not_expr(scope, block)
        
        start = node.span.start
        
        while self.check(TokenType.GATE_AND):
            self.advance()
            
            left = self.logic_not_expr(scope, block)
            
            end = left.span.end
            
            node = BinaryExpr(
                node,
                Operator.AND,
                left,
                Span(start, end, self.file_map)
            )
            
        return node
    
    
    def logic_not_expr(self, scope: Enviroment, block: bool) -> Node:
        if self.check(TokenType.GATE_NOT):
            start = self.tokens._peek(self.position)._span.start
            
            self.advance()
            
            value: Node = self.logic_not_expr(scope, block)
            
            end = value.span.end
            
            if isinstance(value, UnaryExpr):
                if value.operator == Operator.NOT:
                    return value.value
            
            return UnaryExpr(
                Operator.NOT,
                value,
                Span(start, end, self.file_map)
            )
        
        else:
            return self.comparison_expr(scope, block)
    
    
    def comparison_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.term_expr(scope, block)
        
        start = node.span.start
        
        while self.match_token_type(
            TokenType.OPERATOR_GREATER,
            TokenType.OPERATOR_LESS,
            TokenType.OPERATOR_GREATER_EQUAL,
            TokenType.OPERATOR_LESS_EQUAL,
            TokenType.OPERATOR_EQUAL,
            TokenType.OPERATOR_NOT_EQUAL
        ):
            operator = self.TOKEN_TO_OPERATOR[self.tokens._peek(self.position)._type]
                
            self.advance()
            
            left = self.term_expr(scope, block)
            
            end = left.span.end
            
            node = BinaryExpr(
                node,
                operator, 
                left,
                Span(start, end, self.file_map)
            )
        
        return node    
        
    
    def term_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.factor_expr(scope, block)
        
        start = node.span.start
        
        while self.match_token_type(
            TokenType.OPERATOR_PLUS,
            TokenType.OPERATOR_MINUS
        ):
            operator = self.TOKEN_TO_OPERATOR[self.tokens._peek(self.position)._type]
                
            self.advance()
            
            left = self.factor_expr(scope, block)
            
            end = left.span.end
                
            node = BinaryExpr(
                node,
                operator,
                left,
                Span(start, end, self.file_map)
            )
            
        return node
    
    
    def factor_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.unary_expr(scope, block)
        
        start = node.span.start
        
        while self.match_token_type(
            TokenType.OPERATOR_MULT,
            TokenType.OPERATOR_DIV,
            TokenType.OPERATOR_MOD
        ):
            operator = self.TOKEN_TO_OPERATOR[self.tokens._peek(self.position)._type]
                
            self.advance()
            
            left = self.unary_expr(scope, block)
            
            end = left.span.end
            
            node = BinaryExpr(
                node,
                operator,
                left,
                Span(start, end, self.file_map)
            )
            
        return node
    
    
    def unary_expr(self, scope: Enviroment, block: bool) -> Node:    
        if self.check(TokenType.OPERATOR_MINUS):
            start = self.tokens._peek(self.position)._span.start
            
            self.advance()
            
            value: Node = self.unary_expr(scope, block)
            
            end = value.span.end
            
            if isinstance(value, UnaryExpr):
                if value.operator == Operator.NEG:
                    return value.value
                
            return UnaryExpr(
                Operator.NEG,
                value,
                Span(start, end, self.file_map)
            )
            
        elif self.check(TokenType.OPERATOR_PLUS):
            self.advance()
            return self.unary_expr(scope, block)
            
        else:
            return self.exponentiation_expr(scope, block)
    
    
    def exponentiation_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.primitive(scope, block)
        
        start = node.span.start
        
        while self.check(TokenType.OPERATOR_POW):
            self.advance()
            
            left = self.exponentiation_expr(scope, block)
            end = left.span.end
            
            node = BinaryExpr(
                node,
                Operator.POW,
                left,
                Span(start, end, self.file_map)
            )

        return node
    
    
    def primitive(self, scope: Enviroment, block: bool) -> Node:
        # Is a NUMBER?
        if self.check(TokenType.LITERAL_NUMBER):
            current_token = self.tokens._peek(self.position)
                
            if isinstance(current_token._value, float):
                node = FloatLiteral(current_token._value, current_token._span)
            else:
                node = IntLiteral(current_token._value, current_token._span)
                
            self.advance()
            
            return node

        # is a STRING_LITERAL
        elif self.check(TokenType.LITERAL_STRING):
            current_token = self.tokens._peek(self.position)
            node = StringLiteral(current_token._value, current_token._span)
            
            self.advance()
            
            return node
                        
       # is a bool
        elif self.check(TokenType.LITERAL_TRUE):
            span = self.tokens._peek(self.position)._span
            
            self.advance()
            
            return BoolLiteral(1, span)
        
        elif self.check(TokenType.LITERAL_FALSE):
            span = self. tokens._peek(self.position)._span
            
            self.advance()
            
            return BoolLiteral(0, span)
        
        # Is a LPAREN?
        elif self.check(TokenType.LPAREN):
            span_lparen = self.tokens._peek(self.position)._span

            self.advance()
            
            node = self.expression(scope)
            
            if self.check(TokenType.RPAREN):
                self.advance()
                return node
                
            else:
                token = self.tokens._peek(self.position)

                self.diag.emit(
                    ErrorCode.E2003,
                    None,
                    Span(span_lparen.start, token._span.end, self.file_map),
                    (token._span, "`)` was expected here to close the expression")
                )
                
                self.synchronize(block)
                
                return ErrorNode(Span(0, 0, self.file_map))
        
        #Is a identifier?
        elif self.check(TokenType.LITERAL_IDENT):
            var_ident = self.tokens._peek(self.position)
            
            self.advance()
            
            #if self.check(TokenType.LPAREN):
             #   self.advance()
              #  return self.parse_call_function(scope)
              
            return VariableExpr(
                var_ident._value,
                Span(var_ident._span.start, var_ident._span.end, self.file_map)
            )
        
        elif self.check(TokenType.LBRACE):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_block_expr(True, token._span.start, scope, block)
        
        elif self.check(TokenType.KEYWORD_IF):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_if_form(scope, True, token._span.start)
        
        elif self.check(TokenType.KEYWORD_INPUT):
            in_token = self.tokens._peek(self.position)
            self.advance()
            self.advance()
            type_token = self.tokens._peek(self.position)
            match type_token._type:
                case TokenType.KEYWORD_BOOL: type_token = ZonType.BOOL
                case TokenType.KEYWORD_INT: type_token = ZonType.INT
                case TokenType.KEYWORD_FLOAT: type_token = ZonType.FLOAT
                case TokenType.KEYWORD_STRING: type_token = ZonType.STRING
            
            self.advance()
            self.advance()
            prompt = self.primitive(scope, block)
            self.advance()
            
            return InputExpr(
                type_token,
                prompt,
                Span(in_token._span.start, prompt.span.end, self.file_map)
            )
        
        else:
            token = self.tokens._peek(self.position)
            
            self.diag.emit(
                ErrorCode.E2005,
                { "token" : token._value},
                token._span,
                (token._span, "cannot start an expression")
            )
            
            self.synchronize(block)
            
            return ErrorNode(Span(0, 0, self.file_map))

