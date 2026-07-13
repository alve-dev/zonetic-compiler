from zonc.scanner import Token, TokenType, ListTokens
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from zonc.location_file import Span, FileMap


class Normalizer:
    """Converts newlines into semicolons where needed, enforcing a single
    terminator style per file (either newlines or explicit semicolons).

    Zonetic allows two styles:
        - newline style:   statements end at newlines (like Python)
        - semicolon style: statements end at ';'      (like C)

    The first terminator seen in a file locks the style. Mixing styles
    is an error.

    Newlines inside parentheses or brackets are always ignored, so
    multi-line expressions work naturally in both styles.
    """

    # Tokens that can legitimately end a statement. A newline following
    # one of these (at depth 0) is converted to a semicolon.
    _STATEMENT_ENDERS = frozenset({
        TokenType.LITERAL_NUMBER,
        TokenType.LITERAL_STRING,
        TokenType.LITERAL_IDENT,
        TokenType.LITERAL_TRUE,
        TokenType.LITERAL_FALSE,
        TokenType.RPAREN,
        TokenType.RBRACKET,
        TokenType.KEYWORD_CONTINUE,
        TokenType.KEYWORD_BREAK,
        TokenType.KEYWORD_BOOL,
        TokenType.KEYWORD_FLOAT,
        TokenType.KEYWORD_DOUBLE,
        TokenType.KEYWORD_INT64,
        TokenType.KEYWORD_INT32,
        TokenType.KEYWORD_STRING,
        TokenType.KEYWORD_GIVE,
        TokenType.KEYWORD_RETURN,
    })

    def __init__(self, tokens: ListTokens, diag: DiagnosticEngine, file_map: FileMap):
        self._tokens = tokens
        self._pos = 0
        self._diag = diag
        self._file_map = file_map

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    def _is_end(self) -> bool:
        return self._tokens._peek(self._pos)._type == TokenType.EOF

    def _peek_type(self, offset: int) -> TokenType:
        index = self._pos + offset
        if index < 0 or index > self._tokens._len():
            return TokenType.NONE
        return self._tokens._peek(index)._type

    def _current_span(self):
        return self._tokens._peek(self._pos)._span

    def _can_end_statement(self, kind: TokenType) -> bool:
        return kind in self._STATEMENT_ENDERS

    # ------------------------------------------------------------------
    # Error helpers
    # ------------------------------------------------------------------

    def _err_mixed_style(self, span, expected_mode: str, found: str) -> None:
        self._diag.emit(
            ErrorCode.E1001,
            {"mode_tr": expected_mode, "used_tr": found},
            [span],
            [(span, f"unexpected {found}, this file uses {expected_mode} as statement terminators")],
        )

    def _err_stray_semicolon(self, span) -> None:
        self._diag.emit(
            ErrorCode.E1002,
            None,
            [span],
            [(span, "`;` is not valid here, no statement was opened before this")],
        )

    # ------------------------------------------------------------------
    # Newline handling
    # ------------------------------------------------------------------

    def _handle_newline(self, mode_locked: bool, semicolon_mode: bool) -> tuple[bool, bool]:
        """Process a NEWLINE token. Returns (mode_locked, semicolon_mode)."""
        prev_can_end = self._can_end_statement(self._peek_type(-1))
        next_is_brace = self._peek_type(1) == TokenType.LBRACE

        if not prev_can_end or next_is_brace:
            # just whitespace — drop it
            self._tokens._del(self._pos)
            return mode_locked, semicolon_mode

        span = self._current_span()

        if mode_locked and semicolon_mode:
            # file already committed to semicolons, newlines as terminators are wrong
            self._err_mixed_style(span, "semicolons", "newline")
            self._pos += 1
            return mode_locked, semicolon_mode

        # convert newline → semicolon
        self._tokens._replace(self._pos, Token(TokenType.SEMICOLON, ';', span))
        self._pos += 1

        if not mode_locked:
            mode_locked = True
            semicolon_mode = False

        return mode_locked, semicolon_mode

    # ------------------------------------------------------------------
    # Semicolon handling
    # ------------------------------------------------------------------

    def _handle_semicolon(self, depth: int, mode_locked: bool, semicolon_mode: bool) -> tuple[bool, bool]:
        """Process an explicit SEMICOLON token. Returns (mode_locked, semicolon_mode)."""
        span = self._current_span()

        is_stray = (
            depth > 0
            or not self._can_end_statement(self._peek_type(-1))
            or self._peek_type(1) in (TokenType.LBRACE, TokenType.LPAREN)
        )

        if is_stray:
            self._err_stray_semicolon(span)

        elif mode_locked and not semicolon_mode:
            self._err_mixed_style(span, "newlines", "semicolon")

        else:
            if not mode_locked:
                mode_locked = True
                semicolon_mode = True

        self._pos += 1
        return mode_locked, semicolon_mode

    # ------------------------------------------------------------------
    # End-of-file finalization
    # ------------------------------------------------------------------

    def _finalize(self, mode_locked: bool, semicolon_mode: bool) -> None:
        """Insert a trailing semicolon at EOF if needed (newline mode only)."""
        if not self._can_end_statement(self._peek_type(-1)):
            return

        span = self._current_span()

        if not semicolon_mode:
            # newline mode: silently insert the final semicolon
            self._tokens._add(
                Token(TokenType.EOF, "", Span(span.start + 1, span.end + 1, self._file_map))
            )
            self._tokens._replace(
                self._pos,
                Token(TokenType.SEMICOLON, ';', Span(span.start, span.end + 1, self._file_map)),
            )
        else:
            # semicolon mode: the missing ';' before EOF is an error
            span_err = Span(span.start - 1, span.end, self._file_map)
            self._err_mixed_style(span_err, "semicolons", "newline")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def normalize(self) -> ListTokens:
        depth = 0
        semicolon_mode = False
        mode_locked = False

        while not self._is_end():
            kind = self._peek_type(0)

            if kind == TokenType.NEWLINE:
                if depth == 0:
                    mode_locked, semicolon_mode = self._handle_newline(mode_locked, semicolon_mode)
                
                else:
                    # inside parens/brackets — newlines are just whitespace
                    self._tokens._del(self._pos)

            elif kind in (TokenType.LPAREN, TokenType.LBRACKET):
                depth += 1
                self._pos += 1

            elif kind in (TokenType.RPAREN, TokenType.RBRACKET) and depth > 0:
                depth -= 1
                self._pos += 1

            elif kind == TokenType.SEMICOLON:
                mode_locked, semicolon_mode = self._handle_semicolon(depth, mode_locked, semicolon_mode)

            else:
                self._pos += 1

        self._finalize(mode_locked, semicolon_mode)
        return self._tokens