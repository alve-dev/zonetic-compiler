from .token import Token
from .tokentype import TokenType
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from .list_tokens import ListTokens
from zonc.location_file import Span, FileMap


class Lexer:
    def __init__(
        self,
        source: str,
        tokens: ListTokens,
        diagnostic: DiagnosticEngine,
        file_map: FileMap,
        keywords: dict,
    ) -> None:
        self._source = source
        self._source_len = len(source)
        self._pos = 0
        self._diagnostic = diagnostic
        self._tokens = tokens
        self._file_map = file_map
        self._keywords = keywords

    # ------------------------------------------------------------------
    # Core primitives
    # ------------------------------------------------------------------

    def _peek(self, offset: int) -> str:
        """Return the character at pos+offset without consuming it.
        Returns '\\0' if out of bounds."""
        index = self._pos + offset
        if index < 0 or index >= self._source_len:
            return '\0'
        return self._source[index]

    def _advance(self, step: int = 1) -> None:
        self._pos = min(self._pos + step, self._source_len)

    def _is_end(self) -> bool:
        return self._pos >= self._source_len

    def _span(self, length: int) -> Span:
        return Span(self._pos, self._pos + length, self._file_map)

    def _span_from(self, start: int) -> Span:
        return Span(start, self._pos, self._file_map)

    def _add_token(self, kind: TokenType, lexeme: str) -> None:
        self._tokens._add(Token(kind, lexeme, self._span(len(lexeme))))
        self._advance(len(lexeme))

    # ------------------------------------------------------------------
    # Operator scanning helpers
    # ------------------------------------------------------------------

    def _scan_compound(self, base_kind, base_lexeme, assign_kind, assign_lexeme) -> None:
        """Emit base_kind or assign_kind depending on whether '=' follows."""
        if self._peek(1) == '=':
            self._add_token(assign_kind, assign_lexeme)
        else:
            self._add_token(base_kind, base_lexeme)

    # ------------------------------------------------------------------
    # Operator scanners
    # ------------------------------------------------------------------

    def _scan_plus(self) -> None:
        if self._peek(1) == '+':
            self._add_token(TokenType.OPERATOR_CONCAT, '++')
        else:
            self._scan_compound(
                TokenType.OPERATOR_PLUS,        '+',
                TokenType.OPERATOR_PLUS_ASSIGN, '+=',
            )

    def _scan_minus(self) -> None:
        match self._peek(1):
            case '|':
                self._scan_block_comment()
            case '>':
                self._add_token(TokenType.ARROW, '->')
            case '/':
                self._scan_line_comment()
            case _:
                self._scan_compound(
                    TokenType.OPERATOR_MINUS,        '-',
                    TokenType.OPERATOR_MINUS_ASSIGN, '-=',
                )

    def _scan_star(self) -> None:
        if self._peek(1) == '*':
            # advance past first '*' so _scan_compound sees the second
            self._advance(1)
            self._scan_compound(
                TokenType.OPERATOR_POW,        '**',
                TokenType.OPERATOR_POW_ASSIGN, '**=',
            )
        else:
            self._scan_compound(
                TokenType.OPERATOR_MULT,        '*',
                TokenType.OPERATOR_MULT_ASSIGN, '*=',
            )

    def _scan_slash(self) -> None:
        self._scan_compound(
            TokenType.OPERATOR_DIV,        '/',
            TokenType.OPERATOR_DIV_ASSIGN, '/=',
        )

    def _scan_percent(self) -> None:
        self._scan_compound(
            TokenType.OPERATOR_MOD,        '%',
            TokenType.OPERATOR_MOD_ASSIGN, '%=',
        )

    def _scan_equal(self) -> None:
        if self._peek(1) == '=':
            self._advance(1)
            self._scan_compound(
                TokenType.OPERATOR_EQUAL,     '==',
                TokenType.OPERATOR_EQUAL_STR, '===',
            )
        else:
            self._add_token(TokenType.OPERATOR_ASSIGN, '=')

    def _scan_less(self) -> None:
        if self._peek(1) == '<':
            self._add_token(TokenType.OPERATOR_SHIFT_LEFT, '<<')
        else:
            self._scan_compound(
                TokenType.OPERATOR_LESS,       '<',
                TokenType.OPERATOR_LESS_EQUAL, '<=',
            )

    def _scan_greater(self) -> None:
        if self._peek(1) == '>':
            self._add_token(TokenType.OPERATOR_SHIFT_RIGHT, '>>')
        else:
            self._scan_compound(
                TokenType.OPERATOR_GREATER,       '>',
                TokenType.OPERATOR_GREATER_EQUAL, '>=',
            )

    def _scan_bang(self) -> None:
        if self._peek(1) == '=':
            self._advance(1)
            self._scan_compound(
                TokenType.OPERATOR_NOT_EQUAL,     '!=',
                TokenType.OPERATOR_NOT_EQUAL_STR, '!==',
            )
        else:
            self._add_token(TokenType.GATE_NOT, '!')

    def _scan_ampersand(self) -> None:
        if self._peek(1) == '&':
            self._advance(1)
            self._scan_compound(
                TokenType.GATE_AND,              '&&',
                TokenType.OPERATOR_AND_ASSIGN,   '&&=',
            )
        else:
            self._scan_compound(
                TokenType.BIT_AND,               '&',
                TokenType.OPERATOR_BAND_ASSIGN,  '&=',
            )

    def _scan_pipe(self) -> None:
        if self._peek(1) == '|':
            self._advance(1)
            self._scan_compound(
                TokenType.GATE_OR,             '||',
                TokenType.OPERATOR_OR_ASSIGN,  '||=',
            )
        else:
            self._scan_compound(
                TokenType.BIT_OR,              '|',
                TokenType.OPERATOR_BOR_ASSIGN, '|=',
            )

    def _scan_tilde(self) -> None:
        match self._peek(1):
            case '&':
                self._add_token(TokenType.BIT_NAND, '~&')
            case '|':
                self._add_token(TokenType.BIT_NOR, '~|')
            case '^':
                self._add_token(TokenType.BIT_XNOR, '~^')
            case _:
                self._add_token(TokenType.BIT_NOT, '~')

    # ------------------------------------------------------------------
    # Comment scanners
    # ------------------------------------------------------------------

    def _scan_line_comment(self) -> None:
        while not self._is_end() and self._peek(0) != '\n':
            self._advance(1)

    def _scan_block_comment(self) -> None:
        """Nested block comment: -| ... |- (supports nesting)."""
        self._advance(2)  # skip '-|'
        start = self._pos
        depth = 1

        while not self._is_end():
            if self._peek(0) == '|' and self._peek(1) == '-':
                self._advance(2)
                depth -= 1
                if depth == 0:
                    return
            elif self._peek(0) == '-' and self._peek(1) == '|':
                self._advance(2)
                depth += 1
            else:
                self._advance(1)

        # reached EOF without closing the comment
        self._diagnostic.emit(
            ErrorCode.E0002,
            None,
            [Span(start, self._pos - 1, self._file_map)],
            [(Span(self._pos - 1, self._pos, self._file_map),
              "'|-' was expected here to close the comment")],
        )

    # ------------------------------------------------------------------
    # Number scanning
    # ------------------------------------------------------------------

    def _scan_number(self) -> None:
        """Scan an integer or float literal, with optional '_' thousand separators
        and scientific notation (e/E).

        Valid forms:
            42          plain integer
            1_000_000   integer with thousand separators
            3.14        float
            1.5e10      scientific notation
            1.5e+2      scientific with sign
            1.5e-2      scientific with sign
        """
        start = self._pos
        digits = []

        # --- collect integer part ---
        while not self._is_end() and (self._peek(0).isdigit() or self._peek(0) == '_'):
            digits.append(self._peek(0))
            self._advance(1)

        is_float = False

        # --- collect decimal part ---
        if self._peek(0) == '.' and self._peek(1).isdigit():
            is_float = True
            digits.append('.')
            self._advance(1)

            while not self._is_end() and (self._peek(0).isdigit() or self._peek(0) == '_'):
                digits.append(self._peek(0))
                self._advance(1)

                if digits[-1] == '_':
                    while not self._is_end() and (self._peek(0).isdigit() or self._peek(0) == '_' or self._peek(0) == '.'):
                        self._advance(1)
                    span = self._span_from(start)
                    self._diagnostic.emit(
                        ErrorCode.E0008, None, [span],
                        [(span, "'_' separators are not allowed in float literals")],
                    )
                    return

            # second dot is an error
            if self._peek(0) == '.' and self._peek(1).isdigit():
                while not self._is_end() and (self._peek(0).isdigit() or self._peek(0) == '.'):
                    self._advance(1)
                span = self._span_from(start)
                self._diagnostic.emit(
                    ErrorCode.E0005, None, [span],
                    [(span, "this number has too many decimal points")],
                )
                return

        # --- collect exponent part ---
        if self._peek(0) in ('e', 'E'):
            is_float = True
            digits.append('e')
            self._advance(1)

            if self._peek(0) in ('+', '-'):
                digits.append(self._peek(0))
                self._advance(1)

            if not self._peek(0).isdigit():
                span = Span(self._pos - 1, self._pos, self._file_map)
                self._diagnostic.emit(
                    ErrorCode.E0010, None, [span],
                    [(span, "after this point, only digits are allowed")],
                )
                return

            while not self._is_end() and self._peek(0).isdigit():
                digits.append(self._peek(0))
                self._advance(1)

            if self._peek(0) == '.':
                while not self._is_end() and (self._peek(0).isalnum() or self._peek(0) == '.'):
                    self._advance(1)
                span = self._span_from(start)
                self._diagnostic.emit(
                    ErrorCode.E0011, None, [span],
                    [(span, "exponents cannot have decimal points")],
                )
                return

        # --- letter right after a number is always an error ---
        if self._peek(0).isalpha():
            while not self._is_end() and self._peek(0).isalnum():
                self._advance(1)
            token_text = self._source[start:self._pos]
            span = self._span_from(start)
            self._diagnostic.emit(
                ErrorCode.E0006, {"token": token_text}, [span],
                [(span, f"'{token_text}' starts with a digit")],
            )
            return

        # --- validate thousand separators ---
        raw = "".join(digits)
        if '_' in raw:
            error = self._validate_separators(raw, start, is_float)
            if error:
                return

        # --- emit token ---
        clean = raw.replace('_', '')
        value = float(clean) if is_float else int(clean)
        self._tokens._add(
            Token(TokenType.LITERAL_NUMBER, value, self._span_from(start))
        )

    def _validate_separators(self, raw: str, start: int, is_float: bool) -> bool:
        """Validate '_' thousand separators. Returns True if there is an error."""
        span = self._span_from(start)

        # must be exactly groups of 3 digits after the first group
        # e.g. 1_000, 1_000_000 are valid; 1_00, 1_0000 are not
        index = raw.find('.')
        if index != -1:
            raw = raw[:index]

        parts = raw.split('_')

        # first group can be 1-3 digits, rest must be exactly 3
        if not all(p.isdigit() for p in parts):
            self._diagnostic.emit(
                ErrorCode.E0007, {"number": raw}, [span],
                [(span, "consecutive or leading/trailing '_' are not allowed")],
            )
            return True

        if len(parts[0]) == 0 or len(parts[0]) > 3:
            self._diagnostic.emit(
                ErrorCode.E0007, {"number": raw}, [span],
                [(span, "'_' is not separating thousands correctly")],
            )
            return True

        if any(len(p) != 3 for p in parts[1:]):
            self._diagnostic.emit(
                ErrorCode.E0007, {"number": raw}, [span],
                [(span, "'_' is not separating thousands correctly")],
            )
            return True

        return False

    # ------------------------------------------------------------------
    # Identifier / keyword scanning
    # ------------------------------------------------------------------

    def _scan_identifier_or_keyword(self) -> None:
        start = self._pos
        self._advance(1)

        while not self._is_end() and (self._peek(0).isalnum() or self._peek(0) == '_'):
            self._advance(1)

        ident = self._source[start:self._pos]

        if ident == '_':
            span = self._span_from(start)
            self._diagnostic.emit(
                ErrorCode.E0009, None, [span],
                [(span, "identifiers must contain at least one letter or digit")],
            )
            return

        kind = self._keywords.get(ident, TokenType.LITERAL_IDENT)
        self._tokens._add(Token(kind, ident, self._span_from(start)))

    # ------------------------------------------------------------------
    # String scanning
    # ------------------------------------------------------------------

    def _scan_string(self) -> None:
        opening_quote = self._peek(0)
        start = self._pos
        self._advance(1)
        chars = []
        closed = False

        while not self._is_end():
            char = self._peek(0)

            if char == '\\':
                self._scan_string_escape(chars, opening_quote)

            elif char == '\n':
                chars.append('\n')
                self._advance(1)

            elif char == '\t':
                chars.append('\t')
                self._advance(1)

            elif char == opening_quote:
                closed = True
                self._advance(1)
                break

            else:
                chars.append(char)
                self._advance(1)

        if not closed:
            self._diagnostic.emit(
                ErrorCode.E0004,
                {"quote": opening_quote},
                [Span(start, self._pos, self._file_map)],
                [(Span(self._pos - 1, self._pos, self._file_map),
                  f"'{opening_quote}' was expected here to close the string")],
            )
            return

        self._tokens._add(
            Token(TokenType.LITERAL_STRING, "".join(chars), self._span_from(start))
        )

    def _scan_string_escape(self, chars: list, opening_quote: str) -> None:
        """Handle a single escape sequence inside a string literal."""
        next_char = self._peek(1)

        match next_char:
            case 'n':
                chars.append('\n')
                self._advance(2)

            case 't':
                chars.append('\t')
                self._advance(2)

            case '\\':
                chars.append('\\')
                self._advance(2)

            case "'":
                chars.append("'")
                if opening_quote == '"':
                    span = Span(self._pos, self._pos + 2, self._file_map)
                    self._diagnostic.emit(
                        ErrorCode.W0001,
                        {"quote_used": opening_quote, "quote_escape": "'", "name_quote_used": "double"},
                        [span],
                        [(span, r"'\'' here is unnecessary inside a double-quoted string")],
                    )
                self._advance(2)

            case '"':
                chars.append('"')
                if opening_quote == "'":
                    span = Span(self._pos, self._pos + 2, self._file_map)
                    self._diagnostic.emit(
                        ErrorCode.W0001,
                        {"quote_used": opening_quote, "quote_escape": '"', "name_quote_used": "single"},
                        [span],
                        [(span, r'\"" here is unnecessary inside a single-quoted string')],
                    )
                self._advance(2)

            case _:
                span = Span(self._pos, self._pos + 2, self._file_map)
                self._diagnostic.emit(
                    ErrorCode.E0003,
                    {"escape": f"\\{next_char}"},
                    [span],
                    [(span, "this escape sequence is not supported in Zonetic")],
                )
                self._advance(2)

    # ------------------------------------------------------------------
    # Unknown character
    # ------------------------------------------------------------------

    def _scan_unknown(self, char: str) -> None:
        span = self._span(1)
        self._diagnostic.emit(
            ErrorCode.E0001,
            {"char": char},
            [span],
            [(span, "this character is not recognized by Zonetic")],
        )
        self._advance(1)

    # ------------------------------------------------------------------
    # Main scan loop
    # ------------------------------------------------------------------

    def scan(self) -> ListTokens:
        while not self._is_end():
            char = self._peek(0)

            match char:
                case ' ' | '\r' | '\t':
                    self._advance(1)

                case '\n':
                    self._add_token(TokenType.NEWLINE, '\n')

                case ';':
                    self._add_token(TokenType.SEMICOLON, ';')

                case ':':
                    self._add_token(TokenType.COLON, ':')

                case ',':
                    self._add_token(TokenType.COMMA, ',')

                case '(':
                    self._add_token(TokenType.LPAREN, '(')

                case ')':
                    self._add_token(TokenType.RPAREN, ')')

                case '{':
                    self._add_token(TokenType.LBRACE, '{')

                case '}':
                    self._add_token(TokenType.RBRACE, '}')

                case '[':
                    self._add_token(TokenType.LBRACKET, '[')

                case ']':
                    self._add_token(TokenType.RBRACKET, ']')

                case '.':
                    self._add_token(TokenType.DOT, '.')

                case '+':
                    self._scan_plus()

                case '-':
                    self._scan_minus()

                case '*':
                    self._scan_star()

                case '/':
                    self._scan_slash()

                case '%':
                    self._scan_percent()

                case '=':
                    self._scan_equal()

                case '<':
                    self._scan_less()

                case '>':
                    self._scan_greater()

                case '!':
                    self._scan_bang()

                case '&':
                    self._scan_ampersand()

                case '|':
                    self._scan_pipe()

                case '~':
                    self._scan_tilde()

                case '^':
                    self._scan_compound(
                        TokenType.BIT_XOR,             '^',
                        TokenType.OPERATOR_BXOR_ASSIGN, '^=',
                    )

                case _ if char == '_' or char.isalpha():
                    self._scan_identifier_or_keyword()

                case _ if char == '"' or char == "'":
                    self._scan_string()

                case _ if char.isdigit():
                    self._scan_number()

                case _:
                    self._scan_unknown(char)

        self._tokens._add(
            Token(TokenType.EOF, 'EOF', Span(self._source_len, self._source_len, self._file_map))
        )

        return self._tokens