from zonc.scanner import *
from zonc.zonast import *
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from zonc.enviroment import Environment
from zonc.location_file import Span, FileMap
from typing import List, Union
from zonc.utils import levenshtein_zon


class Parser:
    """Recursive-descent parser for Zonetic.

    Consumes a token stream produced by the Lexer + Normalizer and builds
    an AST. Errors are reported through DiagnosticEngine and the parser
    attempts to recover and continue so that multiple errors can be shown
    in a single pass.

    Expression grammar (lowest to highest precedence):
        expression
            logic_or_expr   (||)
            logic_and_expr  (&&)
            bit_wise_or     (|  ~|)
            bit_wise_xor    (^  ~^)
            bit_wise_and    (&  ~&)
            equality_expr   (== != === !==)
            comparison_expr (< > <= >=)
            shifts_expr     (<< >>)
            term_expr       (+ - ++)
            factor_expr     (* / %)
            unary_expr      (- ! ~)
            exponentiation_expr (**)
            primitive
    """

    # Maps compound-assignment tokens to their underlying binary operator.
    # e.g. += becomes ADD so we can desugar x += 1 into x = x + 1.
    _COMPOUND_TO_OPERATOR = {
        TokenType.OPERATOR_PLUS_ASSIGN:  Operator.ADD,
        TokenType.OPERATOR_MINUS_ASSIGN: Operator.SUB,
        TokenType.OPERATOR_MULT_ASSIGN:  Operator.MUL,
        TokenType.OPERATOR_DIV_ASSIGN:   Operator.DIV,
        TokenType.OPERATOR_MOD_ASSIGN:   Operator.MOD,
        TokenType.OPERATOR_POW_ASSIGN:   Operator.POW,
        TokenType.OPERATOR_AND_ASSIGN:   Operator.AND,
        TokenType.OPERATOR_OR_ASSIGN:    Operator.OR,
        TokenType.OPERATOR_BAND_ASSIGN:  Operator.BAND,
        TokenType.OPERATOR_BOR_ASSIGN:   Operator.BOR,
        TokenType.OPERATOR_BXOR_ASSIGN:  Operator.BXOR,
    }

    # Maps infix operator tokens to their AST Operator enum value.
    _TOKEN_TO_OPERATOR = {
        TokenType.OPERATOR_PLUS:          Operator.ADD,
        TokenType.OPERATOR_MINUS:         Operator.SUB,
        TokenType.OPERATOR_MULT:          Operator.MUL,
        TokenType.OPERATOR_DIV:           Operator.DIV,
        TokenType.OPERATOR_MOD:           Operator.MOD,
        TokenType.OPERATOR_GREATER:       Operator.GT,
        TokenType.OPERATOR_GREATER_EQUAL: Operator.GE,
        TokenType.OPERATOR_LESS:          Operator.LT,
        TokenType.OPERATOR_LESS_EQUAL:    Operator.LE,
        TokenType.OPERATOR_EQUAL:         Operator.EQ,
        TokenType.OPERATOR_NOT_EQUAL:     Operator.NE,
        TokenType.GATE_OR:                Operator.OR,
        TokenType.GATE_AND:               Operator.AND,
        TokenType.OPERATOR_POW:           Operator.POW,
        TokenType.BIT_AND:                Operator.BAND,
        TokenType.BIT_XOR:                Operator.BXOR,
        TokenType.BIT_OR:                 Operator.BOR,
        TokenType.BIT_NOT:                Operator.BNOT,
        TokenType.OPERATOR_SHIFT_LEFT:    Operator.SL,
        TokenType.OPERATOR_SHIFT_RIGHT:   Operator.SR,
        TokenType.OPERATOR_CONCAT:        Operator.CONCAT,
        TokenType.OPERATOR_EQUAL_STR:     Operator.EQ_STR,
        TokenType.OPERATOR_NOT_EQUAL_STR: Operator.NE_STR,
        TokenType.BIT_NAND:               Operator.BNAND,
        TokenType.BIT_NOR:                Operator.BNOR,
        TokenType.BIT_XNOR:              Operator.BXNOR,
    }

    def __init__(self, tokens: ListTokens, diag: DiagnosticEngine, file_map: FileMap) -> None:
        self._tokens = tokens
        self._pos = 0
        self._diag = diag
        self._file_map = file_map
        # Tracks user-defined struct types discovered in the pre-scan pass.
        # Maps type name -> ZonType so the parser can resolve them during
        # type annotation parsing.
        self._custom_types: dict[str, ZonType] = {}
        self._next_type_id = 9  # built-in types occupy ids 0-8

    # ------------------------------------------------------------------
    # Token navigation primitives
    # ------------------------------------------------------------------

    def _is_end(self) -> bool:
        return self._tokens._peek(self._pos)._type == TokenType.EOF

    def _advance(self) -> bool:
        if self._is_end():
            return False
        self._pos += 1
        return True

    def _check(self, kind: TokenType) -> bool:
        if self._is_end():
            return False
        return self._tokens._peek(self._pos)._type == kind

    def _match(self, *kinds: TokenType) -> bool:
        for kind in kinds:
            if self._check(kind):
                return True
        return False

    def _current(self) -> Token:
        return self._tokens._peek(self._pos)

    def _error_span(self, token) -> Span:
        """Return a span suitable for error highlighting.
        Semicolons and EOF tokens point just before their position
        so the error underline lands on the meaningful character.
        """
        if token._type == TokenType.SEMICOLON:
            return Span(token._span.end - 2, token._span.end - 1, self._file_map)
        if token._type == TokenType.EOF:
            return Span(token._span.end - 1, token._span.end, self._file_map)
        return token._span

    # ------------------------------------------------------------------
    # Error recovery
    # ------------------------------------------------------------------

    def _recover(self, block: bool, stop: list[TokenType] = None) -> None:
        """Skip tokens until a safe synchronization point is found.

        Without `stop`, recovers to the next statement-starting keyword.
        With `stop`, recovers until one of the given token types is seen.
        """
        while not self._is_end():
            if stop is None:
                if self._match(
                    TokenType.KEYWORD_MUT, TokenType.KEYWORD_INMUT, TokenType.KEYWORD_IF,
                    TokenType.KEYWORD_WHILE, TokenType.KEYWORD_INFINITY, TokenType.LITERAL_IDENT,
                    TokenType.KEYWORD_FUNC, TokenType.KEYWORD_RETURN, TokenType.KEYWORD_GIVE,
                    TokenType.KEYWORD_CONTINUE, TokenType.KEYWORD_BREAK, TokenType.KEYWORD_STRUCT,
                ):
                    return
                if block and self._check(TokenType.RBRACE):
                    self._advance()
                    return
                self._advance()
            else:
                if self._match(*stop):
                    if self._check(TokenType.RBRACE):
                        self._advance()
                    return
                self._advance()

    # ------------------------------------------------------------------
    # AST list helpers
    # ------------------------------------------------------------------

    def _collect(self, stmt_list: list[Node], node) -> None:
        """Append node (or extend with a list of nodes) into stmt_list,
        silently dropping any ErrorNode values.
        """
        if isinstance(node, list):
            stmt_list.extend(n for n in node if not isinstance(n, ErrorNode))
        elif not isinstance(node, ErrorNode):
            stmt_list.append(node)

    # ------------------------------------------------------------------
    # Block and binary expression helpers
    # ------------------------------------------------------------------

    def _consume_block(self, scope: Environment, expects_value: bool, block: bool, open_char: str = '{') -> BlockExpr | ErrorNode:
        token = self._current()
        if token._type != TokenType.LBRACE:
            self._diag.emit(
                ErrorCode.E2009, {"aux_r": open_char, "token": token._value},
                [Span(token._span.start, token._span.end, self._file_map)],
                [(token._span, f"`{open_char}` was expected here to open the block")],
            )
            self._recover(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        self._advance()
        return self.parse_block_expr(expects_value, token._span.start, scope, block)

    def _parse_binary_expr(self, next_parser, token_types: list[TokenType], scope: Environment, block: bool) -> Node:
        node = next_parser(scope, block)
        if isinstance(node, ErrorNode):
            return node
        start = node.span.start

        while self._match(*token_types):
            token = self._current()
            operator = self._TOKEN_TO_OPERATOR[token._type]
            self._advance()

            right = next_parser(scope, block)
            if isinstance(right, ErrorNode):
                return right

            node = BinaryExpr(node, operator, right, Span(start, right.span.end, self._file_map))

        return node

    # ------------------------------------------------------------------
    # Cast expression helper (used in primitive for int64, bool, etc.)
    # ------------------------------------------------------------------

    def _parse_cast(self, zon_type: ZonType, scope: Environment, block: bool) -> Node:
        """Parse a cast expression of the form `TypeName(expr)`."""
        start = self._current()._span.start
        self._advance()  # consume the type keyword

        if self._check(TokenType.LPAREN):
            self._advance()
            val = self.expression(scope, block)
            if self._check(TokenType.RPAREN):
                end = self._current()._span.end
                self._advance()
                return CastExpr(val, zon_type, Span(start, end, self._file_map))

        last_token = self._error_span(self._current())
        span_err = Span(start, last_token.end, self._file_map)
        self._diag.emit(
            ErrorCode.E2034, None, [span_err],
            [(last_token, f"after a cast like `{zon_type.name}`, you need `(value)`.")],
        )
        return ErrorNode(Span(0, 0, self._file_map))

    # ------------------------------------------------------------------
    # Top-level entry point
    # ------------------------------------------------------------------

    def parse_program(self, filename: str) -> Program:
        """Parse the full token stream and return the root Program node.

        Two-pass design:
          1. Pre-scan to register all struct type names so they can be
             referenced before their definition (forward declarations).
          2. Full parse of all statements.
        """
        statements: list[Node] = []
        scope = Environment()

        # Pass 1: collect struct names so type annotations can reference them
        # anywhere in the file, regardless of declaration order.
        while not self._is_end():
            if self._check(TokenType.KEYWORD_STRUCT):
                self._advance()
                if self._check(TokenType.LITERAL_IDENT):
                    name = self._current()
                    self._custom_types[name._value] = ZonType(self._next_type_id, name._value)
                    self._next_type_id += 1
                    self._advance()
                    continue
            self._advance()

        # Pass 2: full parse
        self._pos = 0
        while not self._is_end():
            if self._check(TokenType.SEMICOLON):
                self._advance()
                continue

            node = self.parse_statement(scope, False)
            self._collect(statements, node)

        return Program(statements, scope, filename)

    # ------------------------------------------------------------------
    # Statement parsing
    # ------------------------------------------------------------------

    def parse_statement(self, scope: Environment, block: bool) -> Node:
        if self._match(TokenType.KEYWORD_MUT, TokenType.KEYWORD_INMUT):
            mutable = self._check(TokenType.KEYWORD_MUT)
            start = self._current()._span.start
            self._advance()
            return self.parse_declaration(mutable, scope, start, block)

        elif self._check(TokenType.LITERAL_IDENT):
            token = self._current()
            self._advance()

            if self._check(TokenType.LPAREN):
                self._advance()
                return self.parse_call_func(token, token._span.start, scope, block)

            elif self._check(TokenType.LBRACKET):
                self._advance()
                idx_expr = self.expression(scope, block)
                if self._check(TokenType.RBRACKET):
                    span_idx_expr = Span(token._span.start, self._current()._span.end, self._file_map)
                    self._advance()
                    index_expr = IndexExpr(token._value, idx_expr, span_idx_expr)
                    return self.parse_assignment(scope, index_expr, token._span, token._span.start, block)
                
                else:
                    span_current = self._error_span(self._current())
                    span_error = Span(token._span.start, span_current.end, self._file_map)
                    self._diag.emit(
                        ErrorCode.E2035, None, [span_error], [(span_current, "expected `]`.")]
                    )
                    self._recover(block)
                    return ErrorNode(Span(0, 0, self._file_map))

            elif self._check(TokenType.DOT):
                return self.parse_assignment_field(scope, token, block)

            return self.parse_assignment(scope, token._value, token._span, token._span.start, block)

        elif self._check(TokenType.LBRACE):
            token = self._current()
            self._advance()
            return self.parse_block_expr(False, token._span.start, scope, block)

        elif self._check(TokenType.KEYWORD_GIVE):
            token = self._current()
            self._advance()
            if not block:
                self._diag.emit(ErrorCode.E2012, None, [token._span], [(token._span, "`give` is not inside a block expression")])
                self._recover(block)
                return ErrorNode(Span(0, 0, self._file_map))
            value = self.expression(scope, block)
            return GiveStmt(value, Span(token._span.start, value.span.end, self._file_map))

        elif self._check(TokenType.KEYWORD_IF):
            start = self._current()._span.start
            self._advance()
            return self.parse_if_form(scope, False, start, block)

        elif self._match(TokenType.KEYWORD_ELIF, TokenType.KEYWORD_ELSE):
            token_err = self._current()
            self._diag.emit(ErrorCode.E2011, {"keyword": token_err._value}, [token_err._span], [(token_err._span, "`if` was expected before this `{keyword}`")])
            self._recover(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        elif self._check(TokenType.KEYWORD_WHILE):
            start = self._current()._span.start
            self._advance()
            return self.parse_while_form(scope, start, False, block)

        elif self._check(TokenType.KEYWORD_INFINITY):
            start = self._current()._span.start
            self._advance()
            return self.parse_while_form(scope, start, True, block)

        elif self._check(TokenType.KEYWORD_BREAK):
            token = self._current()
            self._advance()
            return BreakStmt(token._span)

        elif self._check(TokenType.KEYWORD_CONTINUE):
            token = self._current()
            self._advance()
            return ContinueStmt(token._span)

        elif self._check(TokenType.KEYWORD_FUNC):
            start = self._current()._span.start
            self._advance()
            return self.parse_func_form(scope, start, block)

        elif self._check(TokenType.KEYWORD_RETURN):
            token = self._current()
            self._advance()
            if not block:
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2026, None, [span], [(span, "`return` is not inside any block")])
                self._recover(block)
                return ErrorNode(Span(0, 0, self._file_map))

            value: NodeExpr | None = None
            if not self._check(TokenType.SEMICOLON):
                value = self.expression(scope, block)
                span = Span(token._span.start, value.span.end, self._file_map)
            else:
                span = token._span
                self._advance()

            return ReturnStmt(value, span)

        elif self._check(TokenType.KEYWORD_STRUCT):
            token = self._current()
            self._advance()
            return self.parse_struct(token._span.start, scope, block)

        else:
            token_err = self._current()
            self._diag.emit(ErrorCode.E2010, {"token": token_err._value}, [token_err._span], [(token_err._span, "this is not a valid way to start a statement")])
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))

    # ------------------------------------------------------------------
    # Declaration parsing
    # ------------------------------------------------------------------

    def parse_declaration(self, mutable: bool, scope: Environment, start: int, block: bool) -> List[Union[DeclarationStmt, AssignmentStmt]]:
        node = self.parse_single_declaration(mutable, scope, start, block)
        declarations = []

        if isinstance(node, InitializationStmt):
            if not isinstance(node.decl_stmt, ErrorNode) and not isinstance(node.assign_stmt, ErrorNode):
                declarations.append(node)
            else:
                return node
        elif isinstance(node, ErrorNode):
            return node
        else:
            declarations.append(node)

        if self._check(TokenType.COMMA):
            self._advance()
            for declaration in self.parse_declaration(mutable, scope, start, block):
                declarations.append(declaration)
            return declarations

        elif self._match(TokenType.SEMICOLON, TokenType.LBRACE):
            return declarations

        else:
            token = self._current()
            if token._type == TokenType.EOF:
                return ErrorNode(Span(0, 0, self._file_map))

            self._diag.emit(ErrorCode.E2004, {"token": token._value}, [Span(start, token._span.end, self._file_map)], [(token._span, "expected `;` or `,` here to end or continue the declaration")])
            self._advance()
            self._recover(block, [TokenType.SEMICOLON])
            return ErrorNode(Span(0, 0, self._file_map))

    def parse_single_declaration(self, mutable: bool, scope: Environment, start: int, block: bool) -> DeclarationStmt | List[Union[DeclarationStmt, AssignmentStmt]]:
        name_mut = "mutable" if mutable else "inmutable"
        ident = self._current()

        if not self._check(TokenType.LITERAL_IDENT):
            span_end = self._error_span(ident)
            self._diag.emit(ErrorCode.E2001, {"name_mut": name_mut}, [Span(start, span_end.end, self._file_map)], [(span_end, "an identifier was expected here")])
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))

        self._advance()
        var_name = ident._value
        var_type: ZonType

        if self._check(TokenType.COLON):
            self._advance()
            zon_type = self._current()

            match zon_type._type:
                case TokenType.KEYWORD_INT64:
                    if self._tokens._peek(self._pos + 1)._type == TokenType.LBRACKET:
                        self._advance()
                        self._advance()
                        size_node = self.expression(scope, block)
                        if self._check(TokenType.RBRACKET):
                            var_type = ZonType(8, "int64[]", size_node)
                        else:
                            span_current = self._error_span(self._current())
                            span_error = Span(start, span_current.end, self._file_map)
                            self._diag.emit(
                                ErrorCode.E2035, None, [span_error], [(span_current, "expected `]`.")]
                            )
                            self._recover(block)
                            return ErrorNode(Span(0, 0, self._file_map))
                    else:
                        var_type = ZonType(1, "int64")

                case TokenType.KEYWORD_FLOAT:  var_type = ZonType(2, "float")
                case TokenType.KEYWORD_BOOL:   var_type = ZonType(3, "bool")
                case TokenType.KEYWORD_STRING: var_type = ZonType(4, "str")
                case TokenType.KEYWORD_INT32:  var_type = ZonType(6, "int32")
                case TokenType.KEYWORD_DOUBLE: var_type = ZonType(7, "double")
                case TokenType.KEYWORD_VOID:
                    self._diag.emit(ErrorCode.E2018, None, [zon_type._span], [(zon_type._span, "`void` cannot be used as a type here")])
                    self._recover(block)
                    return ErrorNode(Span(0, 0, self._file_map))
                case _:
                    if zon_type._value in self._custom_types:
                        var_type = self._custom_types[zon_type._value]
                    else:
                        suggestion = self._type_suggestion(zon_type._value)
                        span_end = self._error_span(zon_type)
                        self._diag.emit(
                            ErrorCode.E2002, {"type": zon_type._value, "leven": suggestion},
                            [Span(start, span_end.end, self._file_map)],
                            [(span_end, "is not a valid type in Zonetic{leven}")],
                        )
                        self._advance()
                        self._recover(block)
                        return ErrorNode(Span(0, 0, self._file_map))

            end_offset = self._current()._span.end
            self._advance()

        else:
            var_type = ZonType(0, "UNKNOWN")
            end_offset = self._current()._span.end

        if self._check(TokenType.OPERATOR_ASSIGN):
            decl = DeclarationStmt(var_name, mutable, var_type, ident._span, Span(start, end_offset, self._file_map))
            assignment = self.parse_assignment(scope, var_name, ident._span, start, block)
            return InitializationStmt(decl, assignment, Span(decl.span.start, assignment.span.end, self._file_map))
        
        return DeclarationStmt(var_name, mutable, var_type, ident._span, Span(start, end_offset, self._file_map))

    def parse_assignment(self, scope: Environment, target: str | IndexExpr, span_name: Span, start: int, block: bool, node_compoust=None) -> AssignmentStmt:
        token = self._current()
        self._advance()

        if token._type == TokenType.OPERATOR_ASSIGN:
            expr = self.expression(scope, block)
            if isinstance(expr, ErrorNode):
                return expr
            return AssignmentStmt(target, expr, Span(start, expr.span.end, self._file_map), span_name)

        elif token._type in self._COMPOUND_TO_OPERATOR:
            var = node_compoust if node_compoust is not None else VariableExpr(target, token._span)
            right_expr = self.expression(scope, block)
            if isinstance(right_expr, ErrorNode):
                return right_expr
            expr = BinaryExpr(var, self._COMPOUND_TO_OPERATOR[token._type], right_expr, Span(var.span.start, right_expr.span.end, self._file_map))
            return AssignmentStmt(target, expr, Span(start, expr.span.end, self._file_map), span_name)

        else:
            name_err = target.name if isinstance(target, IndexExpr) else target
            span_end = self._error_span(token)
            self._diag.emit(ErrorCode.E2006, {"token": token._value, "name": name_err}, [Span(start, span_end.end, self._file_map)], [(span_end, "expected an assignment operator here")])
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))


    # ------------------------------------------------------------------
    # Block expression
    # ------------------------------------------------------------------

    def parse_block_expr(self, expects_value: bool, start: int, scope_back: Environment, block: bool) -> BlockExpr:
        statements: list[Node] = []
        give_value: GiveStmt = None
        is_value_give = False
        end: int = 0

        scope = Environment(scope_back)

        while True:
            if self._check(TokenType.SEMICOLON):
                self._advance()
                continue

            if self._is_end():
                token_eof = self._current()
                self._diag.emit(
                    ErrorCode.E2008, {"aux_l": '}', "aux_r": '{'},
                    [Span(start, token_eof._span.end - 1, self._file_map)],
                    [(Span(token_eof._span.end - 2, token_eof._span.end - 1, self._file_map), "`}` was expected here to close the block")],
                )
                return ErrorNode(Span(0, 0, self._file_map))

            if self._check(TokenType.RBRACE):
                end = self._current()._span.end
                self._advance()
                break

            node = self.parse_statement(scope, True)

            if isinstance(node, GiveStmt):
                give_value = node
                statements.append(node)
                is_value_give = True
            else:
                self._collect(statements, node)

        span_block = Span(start, end, self._file_map)

        if is_value_give:
            if not expects_value:
                self._diag.emit(ErrorCode.W2001, None, [Span(start, give_value.span.end, self._file_map)], [(give_value.span, "this `give` is unreachable, no value is expected from this block")])
            return BlockExpr(statements, statements.index(give_value), scope, span_block)

        if expects_value:
            end_stmt = statements[-1] if statements else ErrorNode(Span(start, start, self._file_map))
            self._diag.emit(ErrorCode.E2007, None, [Span(start, end_stmt.span.end, self._file_map)], [(end_stmt.span, "`give` with a value was expected here")])
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))

        return BlockExpr(statements, None, scope, span_block)

    # ------------------------------------------------------------------
    # Control flow forms
    # ------------------------------------------------------------------

    def parse_if_form(self, scope_back: Environment, expects_value: bool, start: int, block: bool) -> IfForm:
        elif_branches = []
        else_branch = None
        len_branch = 1

        cond = self.expression(scope_back, block)
        block_expr = self._consume_block(scope_back, expects_value, block)
        if isinstance(block_expr, ErrorNode):
            return block_expr

        if_branch = IfBranch(cond, Span(start, block_expr.span.end, self._file_map), block_expr)
        if self._check(TokenType.SEMICOLON):
            self._advance()

        while self._check(TokenType.KEYWORD_ELIF):
            token_elif = self._current()
            self._advance()
            cond_elif = self.expression(scope_back, block)
            block_elif = self._consume_block(scope_back, expects_value, block)
            if isinstance(block_elif, ErrorNode):
                return block_elif

            elif_branches.append(IfBranch(cond_elif, Span(token_elif._span.start, block_elif.span.end, self._file_map), block_elif))
            len_branch += 1
            if self._check(TokenType.SEMICOLON):
                self._advance()

        if self._check(TokenType.SEMICOLON):
            self._advance()

        if self._check(TokenType.KEYWORD_ELSE):
            token_else = self._current()
            self._advance()
            block_else = self._consume_block(scope_back, expects_value, block)
            if isinstance(block_else, ErrorNode):
                return block_else

            else_branch = IfBranch(BoolLiteral(1, Span(0, 0, self._file_map)), Span(token_else._span.start, block_else.span.end, self._file_map), block_else)
            len_branch += 1

        span_end = (
            else_branch.span.end if else_branch
            else (elif_branches[-1].span.end if elif_branches else if_branch.span.end)
        )

        return IfForm(if_branch, elif_branches or None, else_branch, len_branch, Span(start, span_end, self._file_map))

    def parse_while_form(self, scope_back: Environment, start: int, infinity: bool, block: bool) -> WhileForm:
        cond = BoolLiteral(1, Span(0, 0, self._file_map)) if infinity else self.expression(scope_back, block)
        block_expr = self._consume_block(scope_back, False, block)
        if isinstance(block_expr, ErrorNode):
            return block_expr
        return WhileForm(cond, block_expr, Span(start, block_expr.span.end, self._file_map))

    # ------------------------------------------------------------------
    # Function and struct forms
    # ------------------------------------------------------------------

    def parse_func_form(self, scope: Environment, start: int, block: bool) -> FuncForm:
        params: list[Param] = []

        if not self._check(TokenType.LITERAL_IDENT):
            token = self._current()
            span = self._error_span(token)
            self._diag.emit(ErrorCode.E2013, {"token": token._value}, [span], [(span, "a valid function name was expected here")])
            self._recover(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        name = self._current()
        self._advance()

        if not self._check(TokenType.LPAREN):
            token = self._current()
            span = self._error_span(token)
            self._diag.emit(ErrorCode.E2014, {"token": token._value, "name": name._value}, [span], [(span, "`(` was expected here to open the parameter list")])
            self._recover(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        self._advance()

        while not self._check(TokenType.RPAREN):
            if self._check(TokenType.KEYWORD_MUT):
                mut = True
            elif self._check(TokenType.KEYWORD_INMUT):
                mut = False
            else:
                token = self._current()
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2016, {"token": token._value}, [span], [(span, "`mut` or `inmut` was expected here to start a parameter")])
                self._recover(block, [TokenType.COMMA, TokenType.RPAREN])
                if self._check(TokenType.COMMA):
                    self._advance()
                    continue
                elif self._check(TokenType.RPAREN):
                    break
                else:
                    return ErrorNode(Span(0, 0, self._file_map))

            param_start = self._current()._span.start
            self._advance()

            if not self._check(TokenType.LITERAL_IDENT):
                mut_keyword = "mut" if mut else "inmut"
                token = self._current()
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2017, {"mut_keyword": mut_keyword, "token": token._value}, [span], [(span, "a valid parameter name was expected here")])
                self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                if self._check(TokenType.COMMA):
                    self._advance()
                    continue
                elif self._check(TokenType.RPAREN):
                    break
                else:
                    return ErrorNode(Span(0, 0, self._file_map))

            name_param = self._current()
            self._advance()

            if not self._check(TokenType.COLON):
                token = self._current()
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2020, {"name": token._value}, [span], [(span, "`:` and a valid type were expected here")])
                self._recover(block, [TokenType.COMMA, TokenType.RPAREN])
                if self._check(TokenType.COMMA):
                    self._advance()
                    continue
                elif self._check(TokenType.RPAREN):
                    break
                else:
                    return ErrorNode(Span(0, 0, self._file_map))

            self._advance()
            zontype_token = self._current()
            zontype: ZonType

            match zontype_token._type:
                case TokenType.KEYWORD_INT64:  zontype = ZonType(1, "int64")
                case TokenType.KEYWORD_FLOAT:  zontype = ZonType(2, "float")
                case TokenType.KEYWORD_BOOL:   zontype = ZonType(3, "bool")
                case TokenType.KEYWORD_STRING: zontype = ZonType(4, "str")
                case TokenType.KEYWORD_INT32:  zontype = ZonType(6, "int32")
                case TokenType.KEYWORD_DOUBLE: zontype = ZonType(7, "double")
                case TokenType.KEYWORD_VOID:
                    self._diag.emit(ErrorCode.E2018, None, [zontype_token._span], [(zontype_token._span, "`void` cannot be used as a type here")])
                    self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self._check(TokenType.COMMA):
                        self._advance()
                        continue
                    else:
                        break
                case _:
                    if zontype_token._value in self._custom_types:
                        zontype = self._custom_types[zontype_token._value]
                    else:
                        suggestion = self._type_suggestion(zontype_token._value)
                        span = self._error_span(zontype_token)
                        self._diag.emit(ErrorCode.E2019, {"type": zontype_token._value, "leven": suggestion}, [span], [(span, "`{type}` is not a valid parameter type{leven}")])
                        self._advance()
                        self._recover(block, [TokenType.COMMA, TokenType.RPAREN])
                        if self._check(TokenType.COMMA):
                            self._advance()
                            continue
                        elif self._check(TokenType.RPAREN):
                            break
                        else:
                            return ErrorNode(Span(0, 0, self._file_map))

            param_end = self._current()._span.end
            self._advance()

            default = None
            if self._check(TokenType.OPERATOR_ASSIGN):
                self._advance()
                default = self.expression(scope, False)
                param_end = default.span.end

            params.append(Param(mut, name_param._value, zontype, default, Span(param_start, param_end, self._file_map), name_param._span))

            if self._check(TokenType.COMMA):
                self._advance()
            elif self._check(TokenType.RPAREN):
                break
            else:
                token = self._current()
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2025, {"token": token._value}, [span], [(span, "`,` or `)` was expected here")])
                self._recover(block, [TokenType.KEYWORD_FUNC])
                return ErrorNode(Span(0, 0, self._file_map))

        self._advance()  # consume ')'

        # main is special: it always returns int64 implicitly, no return type syntax allowed
        if name._value == "main" and self._check(TokenType.ARROW):
            span_err = Span(start, self._tokens._list[self._pos]._span.end, self._file_map)
            self._diag.emit(
                ErrorCode.E2033, None, [span_err],
                [(self._tokens._list[self._pos]._span, "remove this return type syntax. Main always returns an implicit int64.")],
            )
            self._recover(block, [TokenType.RBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        if name._value == "main":
            return_type = ZonType(1, "int64")

        elif self._check(TokenType.ARROW):
            self._advance()
            zontype_token = self._current()
            match zontype_token._type:
                case TokenType.KEYWORD_INT64:  return_type = ZonType(1, "int64")
                case TokenType.KEYWORD_FLOAT:  return_type = ZonType(2, "float")
                case TokenType.KEYWORD_BOOL:   return_type = ZonType(3, "bool")
                case TokenType.KEYWORD_STRING: return_type = ZonType(4, "str")
                case TokenType.KEYWORD_VOID:   return_type = ZonType(5, "void")
                case TokenType.KEYWORD_INT32:  return_type = ZonType(6, "int32")
                case TokenType.KEYWORD_DOUBLE: return_type = ZonType(7, "double")
                case _:
                    if zontype_token._value in self._custom_types:
                        return_type = self._custom_types[zontype_token._value]
                    else:
                        suggestion = self._type_suggestion(zontype_token._value)
                        span = self._error_span(zontype_token)
                        self._diag.emit(ErrorCode.E2022, {"token": zontype_token._value, "leven": suggestion}, [span], [(span, "a valid return type or `void` was expected here{leven}")])
                        self._recover(block, [TokenType.LBRACE])
                        return ErrorNode(Span(0, 0, self._file_map))
            self._advance()

        else:
            token = self._current()
            span = self._error_span(token)
            self._diag.emit(ErrorCode.E2021, {"token": token._value}, [span], [(span, "`->` was expected here to declare the return type")])
            self._recover(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        block_expr = self._consume_block(scope, False, block)
        if isinstance(block_expr, ErrorNode):
            return block_expr

        return FuncForm(name._value, params or None, return_type, block_expr, name._span, Span(start, block_expr.span.end, self._file_map))

    def parse_struct(self, start: int, scope: Environment, block: bool) -> StructForm:
        if not self._check(TokenType.LITERAL_IDENT):
            span_err = self._error_span(self._current())
            self._diag.emit(ErrorCode.E2027, None, [span_err], [(span_err, "missing or invalid name for this definition")])
            self._recover(block, [TokenType.LBRACE])
            return ErrorNode(Span(0, 0, self._file_map))

        name = self._current()
        self._advance()

        if block:
            self._diag.emit(ErrorCode.E2015, {"name": name._value}, [name._span], [(name._span, "cannot be defined inside a block")])
            self._recover(block, [TokenType.SEMICOLON])
            return ErrorNode(Span(0, 0, self._file_map))

        block_expr = self._consume_block(scope, False, False)
        if isinstance(block_expr, ErrorNode):
            return block_expr

        return StructForm(name._value, block_expr, self._custom_types[name._value], Span(start, block_expr.span.end, self._file_map), name._span)

    # ------------------------------------------------------------------
    # Call and construct expressions
    # ------------------------------------------------------------------

    def parse_call_func(self, name: Token, start: int, scope: Environment, block: bool) -> CallFunc:
        mode_keyparam = False
        keyparams = {}
        params = []

        while not self._check(TokenType.RPAREN):
            if self._check(TokenType.LITERAL_IDENT) and self._tokens._peek(self._pos + 1)._type == TokenType.OPERATOR_ASSIGN:
                mode_keyparam = True
                name_param = self._current()

                if name_param._value in keyparams:
                    span_keyparam = keyparams[name_param._value][1]
                    self._diag.emit(ErrorCode.E2023, {"name": name_param._value}, [name_param._span, span_keyparam], [(name_param._span, "`{name}` is passed again here"), (span_keyparam, "`{name}` was already passed here")])
                    self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self._check(TokenType.COMMA):
                        self._advance()
                        continue
                    else:
                        break

                self._advance()
                self._advance()
                expr_param = self.expression(scope, block)
                keyparams[name_param._value] = (expr_param, Span(name_param._span.start, expr_param.span.end, self._file_map), name_param._span)

            else:
                if self._check(TokenType.RPAREN):
                    break
                elif not mode_keyparam:
                    expr = self.expression(scope, block)
                    if isinstance(expr, ErrorNode):
                        return expr
                    params.append(expr)
                else:
                    token = self._current()
                    self._diag.emit(ErrorCode.E2024, None, [token._span], [(token._span, "positional parameter not allowed here, use `name=value` instead")])
                    self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self._check(TokenType.COMMA):
                        self._advance()
                        continue
                    else:
                        break

            if self._check(TokenType.COMMA):
                self._advance()
            elif self._check(TokenType.RPAREN):
                break
            else:
                token = self._current()
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2025, {"token": token._value}, [span], [(span, "`,` or `)` was expected here")])
                self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                self._advance()
                return ErrorNode(Span(0, 0, self._file_map))

        end = self._current()._span.end
        self._advance()

        return CallFunc(name._value, params or None, keyparams or None, Span(start, end, self._file_map), name._span)

    def parse_construct_expr(self, name: str, start: int, scope: Environment, block: bool) -> ConstructExpr:
        mode_key_field = False
        key_field_assign = {}
        field_assign = []

        while not self._check(TokenType.RPAREN):
            if self._check(TokenType.LITERAL_IDENT) and self._tokens._peek(self._pos + 1)._type == TokenType.OPERATOR_ASSIGN:
                mode_key_field = True
                name_field = self._current()

                if name_field._value in key_field_assign:
                    span_key_field = key_field_assign[name_field._value][1]
                    self._diag.emit(ErrorCode.E2029, {"field": name_field._value}, [name_field._span, span_key_field], [(name_field._span, "`{field}` is assigned again here"), (span_key_field, "`{field}` was already assigned here")])
                    self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self._check(TokenType.COMMA):
                        self._advance()
                        continue
                    else:
                        break

                self._advance()
                self._advance()
                expr_field = self.expression(scope, block)
                key_field_assign[name_field._value] = (expr_field, Span(name_field._span.start, expr_field.span.end, self._file_map), name_field._span)

            else:
                if self._check(TokenType.RPAREN):
                    break
                elif not mode_key_field:
                    expr = self.expression(scope, block)
                    if isinstance(expr, ErrorNode):
                        return expr
                    field_assign.append(expr)
                else:
                    token = self._current()
                    self._diag.emit(ErrorCode.E2030, {"token": token._value}, [token._span], [(token._span, "positional field assign not allowed here.")])
                    self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                    if self._check(TokenType.COMMA):
                        self._advance()
                        continue
                    else:
                        break

            if self._check(TokenType.COMMA):
                self._advance()
            elif self._check(TokenType.RPAREN):
                break
            else:
                token = self._current()
                span = self._error_span(token)
                self._diag.emit(ErrorCode.E2031, {"token": token._value}, [span], [(span, "`,` or `)` was expected here")])
                self._recover(block, [TokenType.RPAREN, TokenType.COMMA])
                self._advance()
                return ErrorNode(Span(0, 0, self._file_map))

        end = self._current()._span.end
        self._advance()

        return ConstructExpr(name, self._custom_types[name], field_assign or None, key_field_assign or None, Span(start, end, self._file_map))

    # ------------------------------------------------------------------
    # Variable, field, and index expressions
    # ------------------------------------------------------------------

    def parse_variable(self, scope: Environment, block: bool):
        var_ident = self._current()
        self._advance()

        if self._check(TokenType.LPAREN):
            self._advance()
            if var_ident._value in self._custom_types:
                return self.parse_construct_expr(var_ident._value, var_ident._span.start, scope, block)
            return self.parse_call_func(var_ident, var_ident._span.start, scope, block)
            
        elif self._check(TokenType.DOT):
            return self.parse_field_expr(VariableExpr(var_ident._value, var_ident._span), block)
        
        elif self._check(TokenType.LBRACKET):
            self._advance()
            idx_expr = self.expression(scope, block)
            if self._check(TokenType.RBRACKET):
                span_node = Span(var_ident._span.start, self._current()._span.end, self._file_map)
                self._advance()
                return IndexExpr(var_ident._value, idx_expr, span_node)

            else:
                span_current = self._error_span(self._current())
                span_error = Span(var_ident._span.start, span_current.end, self._file_map)
                self._diag.emit(
                    ErrorCode.E2035, None, [span_error], [(span_current, "expected `]`.")]
                )
                self._recover(block)
                return ErrorNode(Span(0, 0, self._file_map))

        return VariableExpr(var_ident._value, var_ident._span)

    def parse_field_expr(self, name: VariableExpr, block: bool):
        node = name
        while self._check(TokenType.DOT):
            dot_token = self._current()
            self._advance()
            if self._check(TokenType.LITERAL_IDENT):
                token_field = self._current()
                node = FieldExpr(node, token_field._value, Span(node.span.start, token_field._span.end, self._file_map))
                self._advance()
            else:
                span_err = Span(name.span.start, dot_token._span.end, self._file_map)
                self._diag.emit(ErrorCode.E2028, None, [span_err], [(span_err, "expected a field name after the dot `.`")])
                self._recover(block)
                return ErrorNode(Span(0, 0, self._file_map))
        return node

    def parse_assignment_field(self, scope: Environment, name: Token, block: bool):
        node = VariableExpr(name._value, name._span)
        last_field_token = None

        while self._check(TokenType.DOT):
            dot_token = self._current()
            self._advance()

            if self._check(TokenType.LITERAL_IDENT):
                if last_field_token is not None:
                    node = FieldExpr(object_name=node, field=last_field_token._value, span=Span(node.span.start, last_field_token._span.end, self._file_map))
                last_field_token = self._current()
                self._advance()
            else:
                token = self._current()
                span_err = Span(token._span.start, dot_token._span.end, self._file_map)
                self._diag.emit(ErrorCode.E2028, None, [span_err], [(span_err, "expected a field name after the dot `.`")])
                self._recover(block)
                return ErrorNode(Span(0, 0, self._file_map))

        if self._match(
            TokenType.OPERATOR_ASSIGN, TokenType.OPERATOR_PLUS_ASSIGN,
            TokenType.OPERATOR_MINUS_ASSIGN, TokenType.OPERATOR_MULT_ASSIGN,
            TokenType.OPERATOR_DIV_ASSIGN, TokenType.OPERATOR_MOD_ASSIGN,
            TokenType.OPERATOR_POW_ASSIGN,
        ):
            assignment = self.parse_assignment(
                scope, last_field_token._value, last_field_token._span,
                last_field_token._span.start, block,
                node_compoust=FieldExpr(node, last_field_token._value, last_field_token._span),
            )
            if isinstance(assignment, ErrorNode):
                return assignment
            return AssignmentFieldStmt(object_name=node, field_assign=assignment, span=Span(node.span.start, assignment.span.end, self._file_map))

        else:
            token_field = self._current()
            self._diag.emit(
                ErrorCode.E2032,
                {"expr": Span(name._span.start, last_field_token._span.end, self._file_map).to_string(), "field": last_field_token._value},
                [name._span],
                [(Span(name._span.start, token_field._span.end, self._file_map), "this expression does nothing on its own")],
            )
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))

    # ------------------------------------------------------------------
    # Expression grammar (precedence climbing)
    # ------------------------------------------------------------------

    def expression(self, scope: Environment, block: bool) -> Node:
        return self.logic_or_expr(scope, block)

    def logic_or_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.logic_and_expr, [TokenType.GATE_OR], scope, block)

    def logic_and_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.bit_wise_or, [TokenType.GATE_AND], scope, block)

    def bit_wise_or(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.bit_wise_xor, [TokenType.BIT_OR, TokenType.BIT_NOR], scope, block)

    def bit_wise_xor(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.bit_wise_and, [TokenType.BIT_XOR, TokenType.BIT_XNOR], scope, block)

    def bit_wise_and(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.equality_expr, [TokenType.BIT_AND, TokenType.BIT_NAND], scope, block)

    def equality_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(
            self.comparison_expr,
            [TokenType.OPERATOR_EQUAL, TokenType.OPERATOR_NOT_EQUAL, TokenType.OPERATOR_NOT_EQUAL_STR, TokenType.OPERATOR_EQUAL_STR],
            scope, block,
        )

    def comparison_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(
            self.shifts_expr,
            [TokenType.OPERATOR_GREATER, TokenType.OPERATOR_LESS, TokenType.OPERATOR_GREATER_EQUAL, TokenType.OPERATOR_LESS_EQUAL],
            scope, block,
        )

    def shifts_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.term_expr, [TokenType.OPERATOR_SHIFT_LEFT, TokenType.OPERATOR_SHIFT_RIGHT], scope, block)

    def term_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.factor_expr, [TokenType.OPERATOR_PLUS, TokenType.OPERATOR_MINUS, TokenType.OPERATOR_CONCAT], scope, block)

    def factor_expr(self, scope: Environment, block: bool) -> Node:
        return self._parse_binary_expr(self.unary_expr, [TokenType.OPERATOR_MULT, TokenType.OPERATOR_DIV, TokenType.OPERATOR_MOD], scope, block)

    def unary_expr(self, scope: Environment, block: bool) -> Node:
        if self._check(TokenType.OPERATOR_MINUS):
            start = self._current()._span.start
            self._advance()
            value = self.unary_expr(scope, block)
            # double negation cancels out: --x -> x
            if isinstance(value, UnaryExpr) and value.operator == Operator.NEG:
                return value.value
            return UnaryExpr(Operator.NEG, value, Span(start, value.span.end, self._file_map))

        elif self._check(TokenType.OPERATOR_PLUS):
            self._advance()
            return self.unary_expr(scope, block)

        elif self._check(TokenType.GATE_NOT):
            start = self._current()._span.start
            self._advance()
            value = self.unary_expr(scope, block)
            # double logical-not cancels out: !!x -> x
            if isinstance(value, UnaryExpr) and value.operator == Operator.NOT:
                return value.value
            return UnaryExpr(Operator.NOT, value, Span(start, value.span.end, self._file_map))

        elif self._check(TokenType.BIT_NOT):
            start = self._current()._span.start
            self._advance()
            value = self.unary_expr(scope, block)
            if isinstance(value, UnaryExpr) and value.operator == Operator.BIT_NOT:
                return value.value
            return UnaryExpr(Operator.BNOT, value, Span(start, value.span.end, self._file_map))

        return self.exponentiation_expr(scope, block)

    def exponentiation_expr(self, scope: Environment, block: bool) -> Node:
        node = self.primitive(scope, block)
        if isinstance(node, ErrorNode):
            return node

        start = node.span.start
        while self._check(TokenType.OPERATOR_POW):
            self._advance()
            right = self.exponentiation_expr(scope, block)
            if isinstance(right, ErrorNode):
                return node
            node = BinaryExpr(node, Operator.POW, right, Span(start, right.span.end, self._file_map))

        return node

    def primitive(self, scope: Environment, block: bool) -> Node:
        if self._check(TokenType.LITERAL_NUMBER):
            token = self._current()
            node = FloatLiteral(token._value, token._span) if isinstance(token._value, float) else IntLiteral(token._value, token._span)
            self._advance()
            return node

        elif self._check(TokenType.LITERAL_STRING):
            token = self._current()
            self._advance()
            return StringLiteral(token._value, token._span)

        elif self._check(TokenType.LITERAL_TRUE):
            span = self._current()._span
            self._advance()
            return BoolLiteral(1, span)

        elif self._check(TokenType.LITERAL_FALSE):
            span = self._current()._span
            self._advance()
            return BoolLiteral(0, span)

        elif self._check(TokenType.LPAREN):
            span_lparen = self._current()._span
            self._advance()
            node = self.expression(scope, block)
            if self._check(TokenType.RPAREN):
                self._advance()
                return node
            self._diag.emit(
                ErrorCode.E2003, None,
                [Span(span_lparen.start, node.span.end, self._file_map)],
                [(Span(node.span.end - 1, node.span.end, self._file_map), "`)` was expected here to close the expression")],
            )
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))

        elif self._check(TokenType.LITERAL_IDENT):
            return self.parse_variable(scope, block)

        elif self._check(TokenType.LBRACE):
            start = self._current()._span.start
            self._advance()
            return self.parse_block_expr(True, start, scope, block)

        elif self._check(TokenType.KEYWORD_IF):
            start = self._current()._span.start
            self._advance()
            return self.parse_if_form(scope, True, start, block)

        elif self._check(TokenType.KEYWORD_INT64):
            return self._parse_cast(ZonType(1, "int64"), scope, block)

        elif self._check(TokenType.KEYWORD_BOOL):
            return self._parse_cast(ZonType(3, "bool"), scope, block)

        elif self._check(TokenType.KEYWORD_FLOAT):
            return self._parse_cast(ZonType(2, "float"), scope, block)

        elif self._check(TokenType.KEYWORD_DOUBLE):
            return self._parse_cast(ZonType(7, "double"), scope, block)

        else:
            token = self._current()
            span = self._error_span(token)
            self._diag.emit(ErrorCode.E2005, {"token": token._value}, [span], [(span, "cannot start an expression")])
            self._recover(block)
            return ErrorNode(Span(0, 0, self._file_map))

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _type_suggestion(self, given: str) -> str:
        """Return a Levenshtein suggestion string for an unknown type name,
        or an empty string if no close match is found.
        """
        candidates = ["int", "int64", "int32", "str", "bool", "float", "double", "void"] + list(self._custom_types)
        match = levenshtein_zon.suggest(given, candidates)
        return f", did you mean?: `{match}`" if match else ""