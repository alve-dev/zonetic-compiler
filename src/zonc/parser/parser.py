from zonc.scanner import *
from zonc.zonast import *
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from zonc.enviroment import Enviroment
from zonc.location_file import Span, FileMap
from typing import List, Union
from zonc.utils import levenshtein_zon

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
        TokenType.OPERATOR_NOT_EQUAL : Operator.NE,
        TokenType.GATE_OR : Operator.OR,
        TokenType.GATE_AND : Operator.AND,
        TokenType.OPERATOR_POW : Operator.POW
    }
    
    LIST_TYPE = {}

    def __init__(self, tokens: ListTokens, diag: DiagnosticEngine, file_map: FileMap) -> None:
        self.tokens = tokens
        self.position = 0
        self.length_list = self.tokens._len()
        self.diag = diag
        self.file_map = file_map
        self.type_enum = 6

    def at_end(self) -> bool:
        return self.tokens._peek(self.position)._type == TokenType.EOF

    def advance(self) -> bool:
        if self.at_end(): return False
        self.position += 1
        return True
    
    def get_error_span(self, token) -> Span:
        if token._type == TokenType.SEMICOLON:
            return Span(token._span.end - 2, token._span.end - 1, self.file_map)
        elif token._type == TokenType.EOF:
            return Span(token._span.end - 1, token._span.end, self.file_map)
        return token._span
    
    def synchronize(self, block: bool, stop: list[TokenType] = None):
        while not self.at_end():
            if stop is None:
                if self.match_token_type(
                    TokenType.KEYWORD_MUT, TokenType.KEYWORD_INMUT, TokenType.KEYWORD_IF,
                    TokenType.KEYWORD_WHILE, TokenType.KEYWORD_INFINITY, TokenType.LITERAL_IDENT,
                    TokenType.KEYWORD_FUNC, TokenType.KEYWORD_RETURN, TokenType.KEYWORD_GIVE,
                    TokenType.KEYWORD_CONTINUE, TokenType.KEYWORD_BREAK, TokenType.KEYWORD_STRUCT
                ): return
                elif block and self.check(TokenType.RBRACE): return
                else: self.advance()
            else:
                if self.match_token_type(*stop): return
                else: self.advance()
    
    def check(self, type: TokenType) -> bool:
        if self.at_end(): return False
        return self.tokens._peek(self.position)._type == type

    def match_token_type(self, *types) -> bool:
        for type in types:
            if self.check(type): return True
        return False
        
    def _add_node_to_list(self, stmt_list: list[Node], node: Union[Node, list[Node], ErrorNode]):
        if isinstance(node, list):
            stmt_list.extend(n for n in node if not isinstance(n, ErrorNode))
        elif not isinstance(node, ErrorNode):
            stmt_list.append(node)
            
    def _consume_block(self, scope: Enviroment, expects_value: bool, block: bool, aux_r: str = '{') -> BlockExpr | ErrorNode:
        token = self.tokens._peek(self.position)
        if token._type != TokenType.LBRACE:
            self.diag.emit(
                ErrorCode.E2009, { "aux_r" : aux_r, "token": token._value},
                [Span(token._span.start, token._span.end, self.file_map)],
                [(token._span, "`{aux_r}` was expected here to open the block")]
            )
            self.synchronize(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self.file_map))
        
        self.advance()
        return self.parse_block_expr(expects_value, token._span.start, scope, block)

    def _parse_binary_expr(self, next_parser, token_types: list[TokenType], scope: Enviroment, block: bool) -> Node:
        node = next_parser(scope, block)
        if isinstance(node, ErrorNode): return node
        start = node.span.start
        
        while self.match_token_type(*token_types):
            token = self.tokens._peek(self.position)
            operator = self.TOKEN_TO_OPERATOR[token._type]
            self.advance()
            
            right = next_parser(scope, block)
            if isinstance(right, ErrorNode): return right
            
            node = BinaryExpr(node, operator, right, Span(start, right.span.end, self.file_map))
            
        return node
    
    def parse_program(self, name_file: str) -> Program:
        statements: list[Node] = []
        scope = Enviroment()
        
        while not self.at_end():
            if self.check(TokenType.KEYWORD_STRUCT):
                self.advance()
                if self.check(TokenType.LITERAL_IDENT):
                    name = self.tokens._peek(self.position)
                    self.LIST_TYPE.update({name._value : ZonType(self.type_enum, name._value)})
                    self.type_enum += 1
                    self.advance()
                    
            self.advance()
        
        self.position = 0
        while not self.at_end():
            if self.check(TokenType.SEMICOLON):
                self.advance()
                continue
            
            node = self.parse_statement(scope, False)
            self._add_node_to_list(statements, node)
            
        return Program(statements, scope, name_file)
    
    def parse_statement(self, scope: Enviroment, block: bool) -> Node:
        if self.match_token_type(TokenType.KEYWORD_MUT, TokenType.KEYWORD_INMUT):
            mut = self.check(TokenType.KEYWORD_MUT)
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_declaration(mut, scope, start, block)
        
        elif self.check(TokenType.LITERAL_IDENT):
            token = self.tokens._peek(self.position)
            self.advance()
            
            if self.check(TokenType.LPAREN):
                self.advance()
                return self.parse_call_func(token, token._span.start, scope, block)
            
            elif self.check(TokenType.DOT):
                return self.parse_assignment_field(scope, token, block)
            
            return self.parse_assignment(scope, token._value, token._span, token._span.start, block)
            
        elif self.check(TokenType.LBRACE):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_block_expr(False, token._span.start, scope, block)
        
        elif self.check(TokenType.KEYWORD_GIVE):
            token = self.tokens._peek(self.position)
            self.advance()
            if not block:
                self.diag.emit(ErrorCode.E2012, None, [token._span], [(token._span, "`give` is not inside a block expression")])
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
            value = self.expression(scope, block)
            return GiveStmt(value, Span(token._span.start, value.span.end, self.file_map))
            
        elif self.check(TokenType.KEYWORD_IF):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_if_form(scope, False, start, block)
        
        elif self.match_token_type(TokenType.KEYWORD_ELIF, TokenType.KEYWORD_ELSE):
            token_err = self.tokens._peek(self.position)
            self.diag.emit(ErrorCode.E2011, { "keyword" : token_err._value }, [token_err._span], [(token_err._span, "`if` was expected before this `{keyword}`")])
            self.synchronize(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self.file_map))
        
        elif self.check(TokenType.KEYWORD_WHILE):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_while_form(scope, start, False, block)
        
        elif self.check(TokenType.KEYWORD_INFINITY):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_while_form(scope, start, True, block)
        
        elif self.check(TokenType.KEYWORD_BREAK):
            token = self.tokens._peek(self.position)
            self.advance()
            return BreakStmt(token._span)
        
        elif self.check(TokenType.KEYWORD_CONTINUE):
            token = self.tokens._peek(self.position)
            self.advance()
            return ContinueStmt(token._span)

        elif self.check(TokenType.KEYWORD_FUNC):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_func_form(scope, start, block)
        
        elif self.check(TokenType.KEYWORD_RETURN):
            token = self.tokens._peek(self.position)
            self.advance()
            if not block:
                span = self.get_error_span(token)
                self.diag.emit(ErrorCode.E2026, None, [span], [(span, "`return` is not inside any block")])
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
            
            value: NodeExpr | None = None 
            span: Span
            if not self.check(TokenType.SEMICOLON):
                value = self.expression(scope, block)
                span = Span(token._span.start, value.span.end, self.file_map)
            else:
                span = token._span
                self.advance()
            
            return ReturnStmt(value, span)
        
        elif self.check(TokenType.KEYWORD_STRUCT):
            token = self.tokens._peek(self.position)
            self.advance()
            return self.parse_struct(token._span.start, scope, block)
    
        else:
            token_err = self.tokens._peek(self.position)
            self.diag.emit(ErrorCode.E2010, { "token" : token_err._value }, [token_err._span], [(token_err._span, "this is not a valid way to start a statement")])
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
        
    def parse_declaration(self, mutable: bool, scope: Enviroment, start: int, block: bool) -> List[Union[DeclarationStmt, AssignmentStmt]]:
        node = self.parse_single_declaration(mutable, scope, start, block)
        declarations = []
        
        if isinstance(node, InitializationStmt):
            if not isinstance(node.decl_stmt, ErrorNode) and not isinstance(node.assign_stmt, ErrorNode): declarations.append(node)
            else: return node
        elif isinstance(node, ErrorNode): return node
        else: declarations.append(node)
        
        if self.check(TokenType.COMMA):
            self.advance()
            for declaration in self.parse_declaration(mutable, scope, start, block):
                declarations.append(declaration)
            return declarations
                
        elif self.check(TokenType.SEMICOLON):
            return declarations
        
        elif self.check(TokenType.LBRACE):
            return declarations
        
        else:
            token = self.tokens._peek(self.position)
            if token._type == TokenType.EOF:
                return ErrorNode(Span(0, 0, self.file_map))
            
            self.diag.emit(ErrorCode.E2004, { "token" : token._value }, [Span(start, token._span.end, self.file_map)], [(token._span, "expected `;` or `,` here to end or continue the declaration")])
            self.advance()
            self.synchronize(block, [TokenType.SEMICOLON])
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
                    case TokenType.KEYWORD_INT64: var_type = ZonType(1, "int64")
                    case TokenType.KEYWORD_FLOAT: var_type = ZonType(2, "float")
                    case TokenType.KEYWORD_BOOL: var_type = ZonType(3, "bool")
                    case TokenType.KEYWORD_STRING: var_type = ZonType(4, "string")
                    case TokenType.KEYWORD_INT32: var_type = ZonType(6, "int32")
                    case TokenType.KEYWORD_DOUBLE: var_type = ZonType(7, "double")
                    case TokenType.KEYWORD_VOID:
                        self.diag.emit(ErrorCode.E2018, None, [zon_type._span], [(zon_type._span, "`void` cannot be used as a type here")])
                        self.synchronize(block)
                        return ErrorNode(Span(0, 0, self.file_map))
                    case _:
                        if zon_type._value in self.LIST_TYPE:
                            var_type = self.LIST_TYPE[zon_type._value]

                        else:
                            list_type = ["int64", "string", "bool", "float", "int32", "double"]
                            for key in self.LIST_TYPE:
                                list_type.append(key)
                            
                            leven = levenshtein_zon.suggest_command(zon_type._value, list_type)
                            if leven is None: leven = ""
                            else: leven = f", did you mean?: `{leven}`"
                                
                            span_end = self.get_error_span(zon_type)
                            self.diag.emit(ErrorCode.E2002, { "type" : zon_type._value, "leven" : leven }, [Span(start, span_end.end, self.file_map)],
                                           [(span_end, "is not a valid type in Zonetic{leven}")])
                            self.advance()
                            self.synchronize(block)
                            return ErrorNode(Span(0, 0, self.file_map))
                
                end_offset = current_span.end
                self.advance()
            else:
                var_type = ZonType(0, "UNKNOWN")
                end_offset = self.tokens._peek(self.position)._span.end
            
            if self.check(TokenType.OPERATOR_ASSIGN):
                decl = DeclarationStmt(var_name, mutable, var_type, ident._span, Span(start, end_offset, self.file_map))
                assing = self.parse_assignment(scope, var_name, ident._span, start, block)
                return InitializationStmt(
                    decl,
                    assing,
                    Span(decl.span.start, assing.span.end, self.file_map)
                )
            else:
                return DeclarationStmt(var_name, mutable, var_type, ident._span, Span(start, end_offset, self.file_map))
        else:
            span_end = self.get_error_span(ident)
            self.diag.emit(ErrorCode.E2001, { "name_mut" : name_mut }, [Span(start, span_end.end, self.file_map)], [(span_end, "an identifier was expected here")])
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
        
    def parse_assignment(self, scope: Enviroment, name: str, span_name: Span, start: int, block: bool, node_compoust = None) -> AssignmentStmt:
        token = self.tokens._peek(self.position)
        self.advance()
        
        if token._type == TokenType.OPERATOR_ASSIGN:
            expr = self.expression(scope, block)
            if isinstance(expr, ErrorNode): return expr
            return AssignmentStmt(name, expr, Span(start, expr.span.end, self.file_map), span_name)
            
        elif token._type in self.COMPOUND_TO_OPERATOR:
            var = None
            if node_compoust is None:
                var = VariableExpr(name, Span(token._span.start, token._span.end, self.file_map))
            else:
                var = node_compoust
            
            right_expr = self.expression(scope, block)
            if isinstance(right_expr, ErrorNode): return right_expr
            expr = BinaryExpr(var, self.COMPOUND_TO_OPERATOR[token._type], right_expr, Span(var.span.start, right_expr.span.end, self.file_map))
            return AssignmentStmt(name, expr, Span(start, expr.span.end, self.file_map), span_name)
            
        else:
            span_end = self.get_error_span(token)
            self.diag.emit(ErrorCode.E2006, { "token" : token._value , "name" : name }, [Span(start, span_end.end, self.file_map)], [(span_end, "expected an assignment operator here")])
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
    
    def parse_block_expr(self, expects_value: bool, start: int, scope_back: Enviroment, block: bool) -> BlockExpr:
        statements: list[Node] = []
        give_value: GiveStmt = None
        is_value_give = False
        end: int = 0
        
        scope = Enviroment(scope_back)
        
        while True:
            if self.check(TokenType.SEMICOLON):
                self.advance()
                continue
            
            if self.at_end():
                token_eof = self.tokens._peek(self.position)
                self.diag.emit(ErrorCode.E2008, {"aux_l": '}', "aux_r" : '{'}, [Span(start, token_eof._span.end-1, self.file_map)], [(Span(token_eof._span.end-2, token_eof._span.end-1, self.file_map), "`{aux_l}` was expected here to close the block")])
                return ErrorNode(Span(0, 0, self.file_map))
            
            if self.check(TokenType.RBRACE):
                end = self.tokens._peek(self.position)._span.end
                self.advance()
                break
            
            node = self.parse_statement(scope, True)
            
            if isinstance(node, GiveStmt):
                give_value = node
                statements.append(node)
                is_value_give = True
            else:
                self._add_node_to_list(statements, node)
        
        span_block = Span(start, end, self.file_map)
        
        if is_value_give:
            if not expects_value:
                self.diag.emit(ErrorCode.W2001, None, [Span(start, give_value.span.end, self.file_map)], [(give_value.span, "this `give` is unreachable, no value is expected from this block")])
            return BlockExpr(statements, statements.index(give_value), scope, span_block)
        else:
            if expects_value:
                end_stmt = statements[-1] if statements else ErrorNode(Span(start, start, self.file_map))
                self.diag.emit(ErrorCode.E2007, None, [Span(start, end_stmt.span.end, self.file_map)], [(end_stmt.span, "`give` with a value was expected here")])
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
        
        return BlockExpr(statements, None, scope, span_block)   
                
    def parse_if_form(self, scope_back: Enviroment, expects_value: bool, start: int, block: bool) -> IfForm:
        elif_branches = []
        else_branch = None
        len_branch = 1
        
        cond = self.expression(scope_back, block)
        block_expr = self._consume_block(scope_back, expects_value, block)
        if isinstance(block_expr, ErrorNode): return block_expr
        
        if_branch = IfBranch(cond, Span(start, block_expr.span.end, self.file_map), block_expr)
        if self.check(TokenType.SEMICOLON): self.advance()
        
        while self.check(TokenType.KEYWORD_ELIF):
            token_elif = self.tokens._peek(self.position)
            self.advance()
            cond_elif = self.expression(scope_back, block)
            block_elif = self._consume_block(scope_back, expects_value, block)
            if isinstance(block_elif, ErrorNode): return block_elif
            
            elif_branches.append(IfBranch(cond_elif, Span(token_elif._span.start, block_elif.span.end, self.file_map), block_elif))
            len_branch += 1
            if self.check(TokenType.SEMICOLON): self.advance()
            
        if self.check(TokenType.SEMICOLON): self.advance()
        if self.check(TokenType.KEYWORD_ELSE):
            token_else = self.tokens._peek(self.position)
            self.advance()
            block_else = self._consume_block(scope_back, expects_value, block)
            if isinstance(block_else, ErrorNode): return block_else
            
            else_branch = IfBranch(BoolLiteral(1, Span(0, 0, self.file_map)), Span(token_else._span.start, block_else.span.end, self.file_map), block_else)
            len_branch += 1
            
        span_end = else_branch.span.end if else_branch else (elif_branches[-1].span.end if elif_branches else if_branch.span.end)
        span_if_form = Span(start, span_end, self.file_map)
        
        if len(elif_branches) < 1: elif_branches = None
        
        return IfForm(if_branch, elif_branches, else_branch, len_branch, span_if_form)
    
    def parse_while_form(self, scope_back: Enviroment, start: int, infinity: bool, block: bool) -> WhileForm:
        cond = BoolLiteral(1, Span(0, 0, self.file_map)) if infinity else self.expression(scope_back, block)
        block_expr = self._consume_block(scope_back, False, block)
        if isinstance(block_expr, ErrorNode): return block_expr
        
        return WhileForm(cond, block_expr, Span(start, block_expr.span.end, self.file_map))
            
    def parse_func_form(self, scope: Enviroment, start: int, block: bool) -> FuncForm:
        name: Token
        params: list[Param] = []
        
        if self.check(TokenType.LITERAL_IDENT):
            name = self.tokens._peek(self.position)
            self.advance()
        else:
            token = self.tokens._peek(self.position)
            span = self.get_error_span(token)
            self.diag.emit(ErrorCode.E2013, { "token" : token._value }, [span], [(span, "a valid function name was expected here")])
            self.synchronize(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self.file_map))
            
        if self.check(TokenType.LPAREN):
            self.advance()
            while not(self.check(TokenType.RPAREN)):
                mut: bool
                if self.check(TokenType.KEYWORD_MUT): mut = True
                elif self.check(TokenType.KEYWORD_INMUT): mut = False
                else:
                    token = self.tokens._peek(self.position)
                    span = self.get_error_span(token)
                    self.diag.emit(ErrorCode.E2016, { "token" : token._value}, [span], [(span, "`mut` or `inmut` was expected here to start a parameter")])
                    self.synchronize(block, [TokenType.COMMA, TokenType.RPAREN])
                    if self.check(TokenType.COMMA):
                        self.advance()
                        continue
                    elif self.check(TokenType.RPAREN): break
                    else: return ErrorNode(Span(0, 0, self.file_map))
                    
                param_start = self.tokens._peek(self.position)._span.start
                self.advance()
                
                name_param: Token
                if self.check(TokenType.LITERAL_IDENT):
                    name_param = self.tokens._peek(self.position)
                else:
                    mut_keyword = "mut" if mut else "inmut"
                    token = self.tokens._peek(self.position)
                    span = self.get_error_span(token)
                    self.diag.emit(ErrorCode.E2017, { "mut_keyword" : mut_keyword, "token" : token._value }, [span], [(span, "a valid parameter name was expected here")])
                    self.synchronize(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self.check(TokenType.COMMA):
                        self.advance()
                        continue
                    elif self.check(TokenType.RPAREN): break
                    else: return ErrorNode(Span(0, 0, self.file_map))
                
                self.advance()
                
                zontype: ZonType
                if self.check(TokenType.COLON):
                    self.advance()
                    zontype_token = self.tokens._peek(self.position)
                    match zontype_token._type:
                        case TokenType.KEYWORD_INT64: zontype = ZonType(1, "int64")
                        case TokenType.KEYWORD_FLOAT: zontype = ZonType(2, "float")
                        case TokenType.KEYWORD_BOOL: zontype = ZonType(3, "bool")
                        case TokenType.KEYWORD_STRING: zontype = ZonType(4, "string")
                        case TokenType.KEYWORD_INT32: zontype = ZonType(6, "int32")
                        case TokenType.KEYWORD_DOUBLE: zontype = ZonType(7, "double")
                        case TokenType.KEYWORD_VOID:
                            self.diag.emit(ErrorCode.E2018, None, [zontype_token._span], [(zontype_token._span, "`void` cannot be used as a type here")])
                            self.synchronize(block, [TokenType.RPAREN, TokenType.COMMA])
                            if self.check(TokenType.COMMA):
                                self.advance()
                                continue
                            else: break
                        case _:
                            if zontype_token._value in self.LIST_TYPE:
                                zontype = self.LIST_TYPE[zontype_token._value]
                            
                            else:
                                list_type = ["int64", "int32", "string", "bool", "float", "double"]
                                for key in self.LIST_TYPE:
                                    list_type.append(key)
                            
                                leven = levenshtein_zon.suggest_command(zontype_token._value, list_type)
                                if leven is None: leven = ""
                                else: leven = f", did you mean?: `{leven}`"
                                
                                span = self.get_error_span(zontype_token)
                                self.diag.emit(ErrorCode.E2019, { "type" : zontype_token._value, "leven" : leven }, [span],
                                [(span, "`{type}` is not a valid parameter type{leven}")])
                                
                                self.advance()
                                self.synchronize(block, [TokenType.COMMA, TokenType.RPAREN])
                                if self.check(TokenType.COMMA):
                                    self.advance()
                                    continue
                                elif self.check(TokenType.RPAREN): break
                                else: return ErrorNode(Span(0, 0, self.file_map))
                else:
                    token = self.tokens._peek(self.position)
                    span = self.get_error_span(token)
                    self.diag.emit(ErrorCode.E2020, { "name" : token._value }, [span], [(span, "`:` and a valid type were expected here")])
                    self.synchronize(block, [TokenType.COMMA, TokenType.RPAREN])
                    if self.check(TokenType.COMMA):
                        self.advance()
                        continue
                    elif self.check(TokenType.RPAREN): break
                    else: return ErrorNode(Span(0, 0, self.file_map))
                    
                param_end = self.tokens._peek(self.position)._span.end
                self.advance()
                
                default = None
                if self.check(TokenType.OPERATOR_ASSIGN):
                    self.advance()
                    default = self.expression(scope, False)
                    param_end = default.span.end
                    
                params.append(Param(mut, name_param._value, zontype, default, Span(param_start, param_end, self.file_map), name_param._span))
                
                if self.check(TokenType.COMMA): self.advance()
                elif self.check(TokenType.RPAREN): break
                else:
                    token = self.tokens._peek(self.position)
                    span = self.get_error_span(token)
                    self.diag.emit(ErrorCode.E2025, { "token" : token._value}, [span], [(span, "`,` or `)` was expected here")])
                    self.synchronize(block, [TokenType.KEYWORD_FUNC])
                    return ErrorNode(Span(0, 0, self.file_map))
        else:
            token = self.tokens._peek(self.position)
            span = self.get_error_span(token)
            self.diag.emit(ErrorCode.E2014, { "token" : token._value, "name" : name._value }, [span], [(span, "`(` was expected here to open the parameter list")])
            self.synchronize(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self.file_map))
        
        self.advance()
        
        return_type: ZonType
        if self.check(TokenType.ARROW):
            self.advance()
            zontype_token = self.tokens._peek(self.position)
            match zontype_token._type:
                case TokenType.KEYWORD_INT64: return_type = ZonType(1, "int")
                case TokenType.KEYWORD_FLOAT: return_type = ZonType(2, "float")
                case TokenType.KEYWORD_BOOL: return_type = ZonType(3, "bool")
                case TokenType.KEYWORD_STRING: return_type = ZonType(4, "string")
                case TokenType.KEYWORD_VOID: return_type = ZonType(5, "void")
                case TokenType.KEYWORD_INT32: return_type = ZonType(6, "int32")
                case TokenType.KEYWORD_DOUBLE: return_type = ZonType(7, "double")
                case _:
                    if zontype_token._value in self.LIST_TYPE:
                        return_type = self.LIST_TYPE[zontype_token._value]
                    
                    else:
                        list_type = ["int64", "int32", "string", "bool", "float", "void"]
                        for key in self.LIST_TYPE:
                            list_type.append(key)
                            
                        leven = levenshtein_zon.suggest_command(zontype_token._value, list_type)
                        if leven is None: leven = ""
                        else: leven = f", did you mean?: `{leven}`"
                        
                        span = self.get_error_span(zontype_token)
                        self.diag.emit(ErrorCode.E2022, { "token" : zontype_token._value, "leven" : leven }, [span],
                        [(span, "a valid return type or `void` was expected here{leven}")])
                        self.synchronize(block, [TokenType.LBRACE])
                        return ErrorNode(Span(0, 0, self.file_map))
        else:
            token = self.tokens._peek(self.position)
            span = self.get_error_span(token)
            self.diag.emit(ErrorCode.E2021, { "token" : token._value }, [span], [(span, "`->` was expected here to declare the return type")])
            self.synchronize(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self.file_map))
        
        self.advance()
        
        block_expr = self._consume_block(scope, False, block)
        if isinstance(block_expr, ErrorNode): return block_expr
            
        if len(params) < 1: params = None
            
        return FuncForm(name._value, params, return_type, block_expr, name._span, Span(start, block_expr.span.end, self.file_map))
    
    def parse_call_func(self, name: Token, start: int, scope: Enviroment, block: bool) -> CallFunc:
        mode_keyparam = False
        keyparams = {}
        params = []
        
        while not self.check(TokenType.RPAREN):        
            if self.check(TokenType.LITERAL_IDENT) and self.tokens._peek(self.position + 1)._type == TokenType.OPERATOR_ASSIGN:
                mode_keyparam = True
                name_param = self.tokens._peek(self.position)
                
                if name_param._value in keyparams:
                    span_keyparam = keyparams[name_param._value][1]
                    self.diag.emit(ErrorCode.E2023, { "name" : name_param._value }, [name_param._span, span_keyparam], [(name_param._span, "`{name}` is passed again here"), (span_keyparam, "`{name}` was already passed here")])
                    self.synchronize(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self.check(TokenType.COMMA):
                        self.advance()
                        continue
                    else: break
                
                self.advance()
                self.advance()
                expr_param = self.expression(scope, block)
                keyparams.update({name_param._value: (expr_param, Span(name_param._span.start, expr_param.span.end, self.file_map), name_param._span)})
                    
            else:
                if self.check(TokenType.RPAREN): break
                elif not mode_keyparam:
                    expr = self.expression(scope, block)
                    if isinstance(expr, ErrorNode): return expr
                    params.append(expr)
                    
                else:
                    token = self.tokens._peek(self.position)
                    self.diag.emit(ErrorCode.E2024, None, [token._span], [(token._span, "positional parameter not allowed here, use `name=value` instead")])
                    self.synchronize(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self.check(TokenType.COMMA):
                        self.advance()
                        continue
                    else: break
            
            if self.check(TokenType.COMMA):
                self.advance()
                continue
            elif self.check(TokenType.RPAREN): break
            else:
                token = self.tokens._peek(self.position)
                span = self.get_error_span(token)
                self.diag.emit(ErrorCode.E2025, { "token" : token._value }, [span], [(span, "`,` or `)` was expected here")])
                self.synchronize(block, [TokenType.RPAREN, TokenType.COMMA])
                self.advance()
                return ErrorNode(Span(0, 0, self.file_map))
                
        end = self.tokens._peek(self.position)._span.end
        self.advance()
            
        if len(params) < 1: params = None
        if len(keyparams) < 1: keyparams = None
                    
        return CallFunc(name._value, params, keyparams, Span(start, end, self.file_map), name._span)

    def parse_struct(self, start: int, scope: Enviroment, block: bool) -> StructForm:
        name: Token 
        
        if self.check(TokenType.LITERAL_IDENT):
            name = self.tokens._peek(self.position)
            self.advance()
        else:
            span_err = self.get_error_span(self.tokens._peek(self.position))
            self.diag.emit(
                ErrorCode.E2027, None, [span_err],
                [(span_err, "missing or invalid name for this definition")]
            )
            self.synchronize(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self.file_map))
        
        if block:
            self.diag.emit(
                ErrorCode.E2015, { "name" : name._value }, [name._span],
                [(name._span, "cannot be defined inside a block")]
            )
            self.synchronize(block, [TokenType.SEMICOLON])
            return ErrorNode(Span(0, 0, self.file_map))
        
        block_expr = self._consume_block(scope, False, False)
        if isinstance(block_expr, ErrorNode): return block_expr
        
        return StructForm(
            name._value,
            block_expr,
            self.LIST_TYPE[name._value],
            Span(start, block_expr.span.end, self.file_map),
            name._span
        )
    
    def parse_variable(self, scope: Enviroment, block: bool):
        var_ident = self.tokens._peek(self.position)
        self.advance()
        if self.check(TokenType.LPAREN):
            self.advance()
            return self.parse_call_func(var_ident, var_ident._span.start, scope, block)
        
        elif self.check(TokenType.LBRACKET):
            self.advance()
            mode_key_field = False
            key_field_assing = {}
            field_assing = []
        
            while not self.check(TokenType.RBRACKET):        
                if self.check(TokenType.LITERAL_IDENT) and self.tokens._peek(self.position + 1)._type == TokenType.OPERATOR_ASSIGN:
                    mode_key_field = True
                    name_field = self.tokens._peek(self.position)
                    
                    if name_field._value in key_field_assing:
                        span_key_field = key_field_assing[name_field._value][1]
                        self.diag.emit(ErrorCode.E2029, { "field" : name_field._value }, [name_field._span, span_key_field], [(name_field._span, "`{field}` is assigned again here"), (span_key_field, "`{field}` was already assigned here")])
                        self.synchronize(block, [TokenType.RBRACKET, TokenType.COMMA])
                        if self.check(TokenType.COMMA):
                            self.advance()
                            continue
                        else: break
                    
                    self.advance()
                    self.advance()
                    expr_field = self.expression(scope, block)
                    key_field_assing.update({name_field._value: (expr_field, Span(name_field._span.start, expr_field.span.end, self.file_map), name_field._span)})
                        
                else:
                    if self.check(TokenType.RBRACKET): break
                    elif not mode_key_field:
                        expr = self.expression(scope, block)
                        if isinstance(expr, ErrorNode): return expr
                        field_assing.append(expr)
                    else:
                        token = self.tokens._peek(self.position)
                        self.diag.emit(ErrorCode.E2030, { "token" : token._value}, [token._span], [(token._span, "positional field assign not allowed here.")])
                        self.synchronize(block, [TokenType.RBRACKET, TokenType.COMMA])
                        if self.check(TokenType.COMMA):
                            self.advance()
                            continue
                        else: break
                
                if self.check(TokenType.COMMA):
                    self.advance()
                    continue
                elif self.check(TokenType.RBRACKET): break
                else:
                    token = self.tokens._peek(self.position)
                    span = self.get_error_span(token)
                    self.diag.emit(ErrorCode.E2031, { "token" : token._value }, [span], [(span, "`,` or `]` was expected here")])
                    self.synchronize(block, [TokenType.RBRACKET, TokenType.COMMA])
                    self.advance()
                    return ErrorNode(Span(0, 0, self.file_map))
                    
            end = self.tokens._peek(self.position)._span.end
            self.advance()
                
            if len(field_assing) < 1: field_assing = None
            if len(key_field_assing) < 1: key_field_assing = None
            
            return ConstructExpr(
                var_ident._value,
                self.LIST_TYPE[var_ident._value] if var_ident._value in self.LIST_TYPE else ZonType(0, "UNKNOWN"),
                field_assing,
                key_field_assing,
                Span(var_ident._span.start, end, self.file_map)
            ) 
        
        elif self.check(TokenType.DOT):
            return self.parse_field_expr(VariableExpr(var_ident._value, Span(var_ident._span.start, var_ident._span.end, self.file_map)), block)
            
        return VariableExpr(var_ident._value, Span(var_ident._span.start, var_ident._span.end, self.file_map))
    
    def parse_field_expr(self, name: VariableExpr, block):
        node = name
        while self.check(TokenType.DOT):
            dot_token = self.tokens._peek(self.position)
            self.advance()
            if self.check(TokenType.LITERAL_IDENT):
                token_field = self.tokens._peek(self.position)
                node = FieldExpr(node, token_field._value, Span(node.span.start, token_field._span.end, self.file_map))
                self.advance()
            
            else:
                span_err = Span(name.span.start, dot_token._span.end, self.file_map)
                self.diag.emit(
                    ErrorCode.E2028, None, [span_err], [(span_err, "expected a field name after the dot `.`")]
                )
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
            
        return node

    def parse_assignment_field(self, scope: Enviroment, name: Token, block: bool):
        node = VariableExpr(name._value, name._span)
        last_field_token = None

        while self.check(TokenType.DOT):
            dot_token = self.tokens._peek(self.position)
            self.advance()
            
            if self.check(TokenType.LITERAL_IDENT):
                # Si ya teníamos un campo anterior, lo empaquetamos en el nodo (Left-Recursive)
                if last_field_token is not None:
                    node = FieldExpr(
                        object_name=node, 
                        field=last_field_token._value, 
                        span=Span(node.span.start, last_field_token._span.end, self.file_map)
                    )
                
                # Actualizamos el último campo encontrado
                last_field_token = self.tokens._peek(self.position)
                self.advance()
            
            else:
                token = self.tokens._peek(self.position)
                span_err = Span(token._span.start, dot_token._span.end, self.file_map)
                self.diag.emit(
                    ErrorCode.E2028, None, [span_err], [(span_err, "expected a field name after the dot `.`")]
                )
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
            
        if self.match_token_type(
            TokenType.OPERATOR_ASSIGN,
            TokenType.OPERATOR_PLUS_ASSIGN,
            TokenType.OPERATOR_MINUS_ASSIGN,
            TokenType.OPERATOR_MULT_ASSIGN,
            TokenType.OPERATOR_DIV_ASSIGN,
            TokenType.OPERATOR_MOD_ASSIGN,
            TokenType.OPERATOR_POW_ASSIGN
        ):
            # Parseamos la asignación utilizando solo el ÚLTIMO campo como target
            assignment = self.parse_assignment(
                scope, 
                last_field_token._value, 
                last_field_token._span, 
                last_field_token._span.start, 
                block,
                node_compoust = FieldExpr(node, last_field_token._value, last_field_token._span)
            )
            
            if isinstance(assignment, ErrorNode): 
                return assignment
            
            return AssignmentFieldStmt(
                object_name=node, 
                field_assign=assignment, 
                span=Span(node.span.start, assignment.span.end, self.file_map)
            )
        
        else:
            token_field = self.tokens._peek(self.position)
            self.diag.emit(
                ErrorCode.E2032, 
                { "expr": Span(name._span.start, last_field_token._span.end, self.file_map).to_string(), "field" : last_field_token._value }, 
                [name._span],
                [(Span(name._span.start, token_field._span.end, self.file_map), "this expression does nothing on its own")]
            )
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))
    
    def expression(self, scope: Enviroment, block: bool) -> Node:
        return self.logic_or_expr(scope, block)

    def logic_or_expr(self, scope: Enviroment, block: bool) -> Node:
        return self._parse_binary_expr(self.logic_and_expr, [TokenType.GATE_OR], scope, block)
    
    def logic_and_expr(self, scope: Enviroment, block: bool) -> Node:
        return self._parse_binary_expr(self.logic_not_expr, [TokenType.GATE_AND], scope, block)
    
    def logic_not_expr(self, scope: Enviroment, block: bool) -> Node:
        if self.check(TokenType.GATE_NOT):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            value: Node = self.logic_not_expr(scope, block)
            if isinstance(value, UnaryExpr) and value.operator == Operator.NOT:
                return value.value
            return UnaryExpr(Operator.NOT, value, Span(start, value.span.end, self.file_map))
        return self.equality_expr(scope, block)
    
    def equality_expr(self, scope:Enviroment, block: bool) -> Node:
        return self._parse_binary_expr(
            self.comparison_expr,
            [TokenType.OPERATOR_EQUAL, TokenType.OPERATOR_NOT_EQUAL],
            scope, block
        )
    
    def comparison_expr(self, scope: Enviroment, block: bool) -> Node:
        return self._parse_binary_expr(
            self.term_expr,
            [TokenType.OPERATOR_GREATER, TokenType.OPERATOR_LESS, TokenType.OPERATOR_GREATER_EQUAL, 
             TokenType.OPERATOR_LESS_EQUAL],
            scope, block
        )
        
    def term_expr(self, scope: Enviroment, block: bool) -> Node:
        return self._parse_binary_expr(self.factor_expr, [TokenType.OPERATOR_PLUS, TokenType.OPERATOR_MINUS], scope, block)
    
    def factor_expr(self, scope: Enviroment, block: bool) -> Node:
        return self._parse_binary_expr(self.unary_expr, [TokenType.OPERATOR_MULT, TokenType.OPERATOR_DIV, TokenType.OPERATOR_MOD], scope, block)
    
    def unary_expr(self, scope: Enviroment, block: bool) -> Node:    
        if self.check(TokenType.OPERATOR_MINUS):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            value: Node = self.unary_expr(scope, block)
            if isinstance(value, UnaryExpr) and value.operator == Operator.NEG:
                return value.value
            return UnaryExpr(Operator.NEG, value, Span(start, value.span.end, self.file_map))
        elif self.check(TokenType.OPERATOR_PLUS):
            self.advance()
            return self.unary_expr(scope, block)
        else:
            return self.exponentiation_expr(scope, block)
    
    def exponentiation_expr(self, scope: Enviroment, block: bool) -> Node:
        node = self.primitive(scope, block)
        if isinstance(node, ErrorNode): return node
        
        start = node.span.start

        while self.check(TokenType.OPERATOR_POW):
            self.advance()
            right = self.exponentiation_expr(scope, block)
            if isinstance(right, ErrorNode): return node
            
            end = right.span.end
            node = BinaryExpr(node, Operator.POW, right, Span(start, end, self.file_map))
            
        return node
    
    def primitive(self, scope: Enviroment, block: bool) -> Node:
        if self.check(TokenType.LITERAL_NUMBER):
            current_token = self.tokens._peek(self.position)
            node = FloatLiteral(current_token._value, current_token._span) if isinstance(current_token._value, float) else IntLiteral(current_token._value, current_token._span)
            self.advance()
            return node

        elif self.check(TokenType.LITERAL_STRING):
            current_token = self.tokens._peek(self.position)
            self.advance()
            return StringLiteral(current_token._value, current_token._span)
                        
        elif self.check(TokenType.LITERAL_TRUE):
            span = self.tokens._peek(self.position)._span
            self.advance()
            return BoolLiteral(1, span)
        
        elif self.check(TokenType.LITERAL_FALSE):
            span = self. tokens._peek(self.position)._span
            self.advance()
            return BoolLiteral(0, span)
        
        elif self.check(TokenType.LPAREN):
            span_lparen = self.tokens._peek(self.position)._span
            self.advance()
            node = self.expression(scope, block)
            
            if self.check(TokenType.RPAREN):
                self.advance()
                return node
            else:
                token = self.tokens._peek(self.position)
                self.diag.emit(ErrorCode.E2003, None, [Span(span_lparen.start, node.span.end, self.file_map)], [(Span(node.span.end-1, node.span.end, self.file_map), "`)` was expected here to close the expression")])
                self.synchronize(block)
                return ErrorNode(Span(0, 0, self.file_map))
        
        elif self.check(TokenType.LITERAL_IDENT):
            return self.parse_variable(scope, block)
        
        elif self.check(TokenType.LBRACE):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_block_expr(True, start, scope, block)
        
        elif self.check(TokenType.KEYWORD_IF):
            start = self.tokens._peek(self.position)._span.start
            self.advance()
            return self.parse_if_form(scope, True, start, block)
        
        else:
            token = self.tokens._peek(self.position)
            span = self.get_error_span(token)
            
            self.diag.emit(ErrorCode.E2005, { "token" : token._value}, [span], [(span, "cannot start an expression")])
            self.synchronize(block)
            return ErrorNode(Span(0, 0, self.file_map))