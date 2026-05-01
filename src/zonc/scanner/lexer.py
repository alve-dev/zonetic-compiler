from .token import Token
from .tokentype import TokenType
from zonc.zonc_errors import DiagnosticEngine
from .list_tokens import ListTokens
from zonc.location_file import Span
from zonc.zonc_errors import ErrorCode
from zonc.location_file import FileMap

class Lexer: 
    def __init__(self, code: str, tokens: ListTokens, diagnostic: DiagnosticEngine, file_map: FileMap, keywords: dict) -> None:
        self._code = code
        self._code_len = len(self._code)
        self._position = 0
        self._diagnostic = diagnostic
        self._tokens = tokens
        self._file_map = file_map
        self.keywords = keywords
        
        
    def _generic_span(self, step: int) -> Span:
        return Span(self._position, self._position + step, self._file_map)
    
    
    def _advance(self, step: int):
        if self._position + step > self._code_len:
            self._position = self._code_len
            return
        
        self._position += step
    
    
    def _peek(self, step: int) -> str:
        """peek(0) == actual character
        \npeek(n) == character n times ahead
        \npeek(-n) == character n times back"""
        
        
        if self._position + step >= self._code_len or self._position + step < 0:
            return '\0'
        
        return self._code[self._position + step]
    
    
    def _is_end(self) -> bool:
        return self._position == self._code_len
    
    
    def _match_next(self, expected: str, true_type, true_lexeme, false_type, false_lexeme):
        if self._peek(1) == expected:
            self._tokens._add(
                Token(
                    true_type,
                    true_lexeme,
                    self._generic_span(len(true_lexeme))
                )
            )
            self._advance(len(true_lexeme))
        
        else:
            self._tokens._add(
                Token(
                    false_type,
                    false_lexeme,
                    self._generic_span(len(false_lexeme))
                )
            )
            self._advance(len(false_lexeme))
    
    
    def _scan_plus(self):
        self._match_next(
            '=',
            # Compound Addition Operator
            TokenType.OPERATOR_PLUS_ASSIGN,
            "+=",
            
            # Addition Operator
            TokenType.OPERATOR_PLUS,
            '+'
        )


    def _scan_minus(self):
        match self._peek(1):
            # Multi-Line Comment
            case '|':
                self._advance(2)
                success = False
                start_position = self._position
                count = 1

                while not self._is_end():
                    match self._peek(0):
                        case '|':
                            match self._peek(1):
                                case '-':
                                    self._advance(2)
                                    count -= 1
                                    if count == 0:
                                        success = True
                                        break
                                
                                case _:
                                    self._advance(2)
                                    
                        case '-':
                            match self._peek(1):
                                case '|':
                                    self._advance(2)
                                    count += 1
                                    
                                case _:
                                    self._advance(1)
                                    
                        case _:
                            self._advance(1)
                            
                if not success:
                    self._diagnostic.emit(
                        ErrorCode.E0002,
                        None,
                        [Span(start_position, self._position-1, self._file_map)],
                        [(Span(self._position-1, self._position, self._file_map), "|-` was expected here to close the comment")]
                    )
            
            case '>':
                self._tokens._add(
                    Token(
                        TokenType.ARROW,
                        "->",
                        self._generic_span(2)
                    )
                )
                self._advance(2)
                
            case '/':
                while not self._is_end() and not self._peek(0) == '\n':
                    self._advance(1)
            
            case _:
                self._match_next(
                    '=',
                    # Compound Subtraction Operator
                    TokenType.OPERATOR_MINUS_ASSIGN,
                    "-=",
                    
                    # Subtraction Operator
                    TokenType.OPERATOR_MINUS,
                    '-'
                )
            

    def _scan_star(self):
        match self._peek(1):
            
            # Possible Exponentiation Operator
            case '*':
                self._advance(1)
                self._match_next(
                    '=',
                    # Compound Exponentiation Operator
                    TokenType.OPERATOR_POW_ASSIGN,
                    "**=",
                    
                    # Exponentiation Operator
                    TokenType.OPERATOR_POW,
                    "**"
                )
                
            # Compound Multiplication Operator
            case _:
                self._match_next(
                    '=',
                    # Compound Multiplication Operator
                    TokenType.OPERATOR_MULT_ASSIGN,
                    "*=",
                    
                    # Multiplication Operator
                    TokenType.OPERATOR_MULT,
                    '*'
                )
    
    
    def _scan_slash(self):
        self._match_next(
            '=',
            # Compound Floating Division Operator
            TokenType.OPERATOR_DIV_ASSIGN,
            "/=",
            
            # Floating Division Operator
            TokenType.OPERATOR_DIV,
            '/'
        )


    def _scan_percentage(self):
        self._match_next(
            '=',
            
            # Compound Mod Operator
            TokenType.OPERATOR_MOD_ASSIGN,
            "%=",
            
            # Mod Operator
            TokenType.OPERATOR_MOD,
            '%'
        )
    
    
    def _scan_equal(self):
        self._match_next(
            '=',
            # Equal Operator
            TokenType.OPERATOR_EQUAL,
            "==",
            
            # Assign Operator
            TokenType.OPERATOR_ASSIGN,
            '=',
        )    
    
    def _scan_less(self):
        match self._peek(1):
            # TODO: COMMING SOON Left Shift Operator
            case '<':
                pass
            
            case _:
                self._match_next(
                    '=',
                    # Less Or Equal Than Operator
                    TokenType.OPERATOR_LESS_EQUAL,
                    "<=",
                    
                    # Less Than Operator
                    TokenType.OPERATOR_LESS,
                    '<'
                )
        
        
    def _scan_greater(self):
        match self._peek(1):
            # TODO Right Shift Operator
            case '>':
                pass
            
            case _:
                self._match_next(
                    '=',
                    # Greater Or Equal Than Operator
                    TokenType.OPERATOR_GREATER_EQUAL,
                    ">=",
                    
                    # Greater Than Operator
                    TokenType.OPERATOR_GREATER,
                    '>'
                )


    def _scan_bang(self):
        match self._peek(1):
            # TODO: COMMING SOON -> FACTORIAL OPERATOR
            #case '!':
            #   pass
            
            case _:
                self._match_next(
                    '=',
                    # Not Equal Than Operator
                    TokenType.OPERATOR_NOT_EQUAL,
                    "!=",
                    
                    # Alt NOT Boolwise Operator
                    TokenType.GATE_NOT,
                    '!'
                )
                
                     
    def _scan_ampersand(self):
        # EN el futuro usar self._match_next para esta cuando se agregue AND bitwise
        
        match self._peek(1):
            # Alternative AND Bool-Wise Operator
            case '&':
                self._tokens._add(
                    Token(
                        TokenType.GATE_AND,
                        "&&",
                        self._generic_span(2)
                    )
                )
                self._advance(2)
            
            #TODO: COMMING SOON -> AND Bit-Wise Operator
            case _:
                pass
    
    
    def _scan_pipe(self):
        # HACER LOS MISMO QUE AND ARRIBA
        match self._peek(1):
            # Alternative OR Bool-Wise Operator
            case '|':
                self._tokens._add(
                    Token(
                        TokenType.GATE_OR,
                        "||",
                        self._generic_span(2)
                    )
                )
                self._advance(2)
            
            # TODO: COMMING SOON -> OR Bit-Wise Operator
            case _:
                pass
    
    
    def _scan_other(self, char: str):
        # Identifier or Keyword
        if char == '_' or char.isalpha():
            self._scan_identifier_or_keyword()
        
        # Literal String
        elif char == '"' or char == "'":
            self._scan_literal_string()
        
        # Literal Number
        elif char.isdigit():
            self._scan_literal_number()
        
        # ERROR DE CHARACTER NO SOPORTADO
        else:
            span = self._generic_span(1)
            
            self._diagnostic.emit(
                ErrorCode.E0001,
                {"char": char},
                [span],
                [(span, "this character is not recognized by Zonetic")]
            )
            self._advance(1)
    
        
    def _scan_literal_number(self) -> None:
        start_position = self._position
        numero_completo = [self._peek(0)]
        self._advance(1)
        is_float = False
        is_error = False
        digit_sequence = 1
        is_separate = False
        
        while not self._is_end():
            char = self._peek(0)
            if char.isdigit():
                if is_separate and digit_sequence >= 3:
                    while self._peek(0).isdigit() or self._peek(0) == '_':
                        self._advance(1)
                            
                    span_error = Span(start_position, self._position, self._file_map)
                    self._diagnostic.emit(
                        ErrorCode.E0007, { "number" : span_error.to_string() }, [span_error],
                        [(span_error, "`_` is not separating thousands here")]
                    )
                    is_error = True
                    break
                
                digit_sequence += 1
                numero_completo.append(char)
                self._advance(1)
            
            elif char == '.' and self._peek(1).isdigit():
                if is_separate and digit_sequence != 3:
                    while self._peek(0).isdigit() or self._peek(0) == '.' or self._peek(0) == '_':
                        self._advance(1)
                    span_error = Span(start_position, self._position, self._file_map)
                    self._diagnostic.emit(
                        ErrorCode.E0007, { "number" : span_error.to_string() }, [span_error],
                        [(span_error, "`_` is not separating thousands here")]
                    )
                    is_error = True
                    break

                if is_float:
                    self._advance(1)
                    while (self._peek(0).isdigit() or self._peek(0) == '.') and not(self._is_end()):
                        self._advance(1)
                    span = Span(start_position, self._position, self._file_map)
                    self._diagnostic.emit(ErrorCode.E0005, None, [span], [(span, "this number has too many decimal points")])
                    is_error = True
                    break
                else:
                    is_float = True
                    is_separate = False
                    digit_sequence = 0
                
                numero_completo.append(char)
                self._advance(1)
            
            elif char == '_':
                if is_float:
                    while self._peek(0).isdigit() or self._peek(0) == '_':
                        self._advance(1)
                    span_error = Span(start_position, self._position, self._file_map)
                    self._diagnostic.emit(ErrorCode.E0008, None, [span_error], [(span_error, "`_` found in decimal part")])
                    is_error = True
                    break
                
                if is_separate and digit_sequence < 3:
                    while self._peek(0).isdigit() or self._peek(0) == '_':
                        self._advance(1)
                    span_error = Span(start_position, self._position, self._file_map)
                    self._diagnostic.emit(ErrorCode.E0007, { "number" : span_error.to_string() }, [span_error], [(span_error, "`_` is not separating thousands here")])
                    is_error = True
                    break
                
                is_separate = True
                digit_sequence = 0
                self._advance(1)
                
            elif char in ['e', 'E']:
                is_float = True
                minimun_num = False
                numero_completo.append('e')
                self._advance(1)
                char = self._peek(0)
                if  char in ['+', '-']:
                    numero_completo.append(char)
                    self._advance(1)
                    
                while not self._is_end():
                    char = self._peek(0)
                    if char.isdigit():
                        numero_completo.append(self._peek(0))
                        self._advance(1)
                        minimun_num = True
                        
                    elif char == '.':
                        while not self._is_end() and self._peek(0).isalnum() or self._peek(0) in ['.']:
                            self._advance(1)
                        
                        span_err = Span(start_position, self._position, self._file_map)
                        self._diagnostic.emit(
                            ErrorCode.E0011, None, [span_err], [(span_err, "exponents cannot have decimal points")]
                        )
                        is_error = True
                        break
                        
                    elif char.isalpha() or char == '_':
                        while not self._is_end() and self._peek(0).isalnum() or self._peek(0) == ['.', '_']:
                            self._advance(1)
                        
                        span_err = Span(start_position, self._position, self._file_map)
                        self._diagnostic.emit(
                            ErrorCode.E0012, None, [span_err], [(span_err, "only digits are allowed here")]
                        )
                        is_error = True
                        break
                    
                    else:
                        if not minimun_num:
                            is_error = True
                            span_err = Span(self._position-1, self._position, self._file_map)
                            self._diagnostic.emit(
                                ErrorCode.E0010, None, [span_err], [(span_err, "After this point, only digits are allowed.")]
                            )
                        break
                
                break
                      
            elif char.isalpha():
                self._advance(1)
                while not self._is_end() and self._peek(0).isalnum() or char == '_':
                    self._advance(1)
                token = self._code[start_position : self._position]
                span = Span(start_position, self._position, self._file_map)
                self._diagnostic.emit(ErrorCode.E0006, { "token" : token}, [span], [(span, f"`{token}` starts with a digit")])
                is_error = True
                break
            
            else:
                break
            
        if not is_error and is_separate and not is_float:
            if digit_sequence != 3:
                span_error = Span(start_position, self._position, self._file_map)
                self._diagnostic.emit(
                    ErrorCode.E0007, { "number" : span_error.to_string() }, [span_error],
                    [(span_error, "`_` is not separating thousands here")]
                )
                is_error = True
            
        if is_error: return
        
        numero = "".join(numero_completo)
        val = float(numero) if is_float else int(numero)
        self._tokens._add(Token(TokenType.LITERAL_NUMBER, val, Span(start_position, self._position, self._file_map)))

                
                
    def _scan_identifier_or_keyword(self) -> None:
        start_position = self._position
        self._advance(1)
                                
        while not self._is_end():
            char = self._peek(0)
            if not (char.isalnum() or char == '_'):
                break
            
            self._advance(1)
            
        ident = self._code[start_position : self._position]
        
        if ident == "_":
            span_err = Span(start_position, self._position, self._file_map)
            self._diagnostic.emit(
                ErrorCode.E0009, None, [span_err], [(span_err, "identifiers must contain at least one letter or digit")]
            )
            return
        
        if ident in self.keywords:
            self._tokens._add(
                Token(
                    self.keywords[ident],
                    ident,
                    Span(start_position, self._position, self._file_map)
                    )
                )
        else:
            self._tokens._add(
                Token(
                    TokenType.LITERAL_IDENT, 
                    ident,
                    Span(start_position, self._position, self._file_map)
                    )
                )


    def _scan_literal_string(self) -> None:
        start_quotes = self._peek(0)
        start_position = self._position
        self._advance(1)
        success: bool = False
        chars = []
        
        while not self._is_end():
            char = self._peek(0)
            match char:
                # Escapes
                case '\\':
                    match self._peek(1):
                        # Escape Newline
                        case 'n':
                            chars.append('\n')
                            self._advance(2)
                            
                        # Escape Tab
                        case 't':
                            chars.append('\t')
                            self._advance(2)
                            
                        # Escape `\`
                        case '\\':
                            chars.append('\\')
                            self._advance(2)
                            
                        # Escape `'`
                        case "'":
                            chars.append("'")
                            
                            # Warning de codigo basura al escapar una comilla que no necesita ser escapada
                            if start_quotes == '"':
                                span = Span(self._position, self._position + 2, self._file_map)
                                
                                self._diagnostic.emit(
                                    ErrorCode.W0001,
                                    { "quote_used" : start_quotes,
                                      "quote_escape" : "'",
                                      "name_quote_used" : "double" },
                                    [span],
                                    [(span, f"`\\'` here is unnecessary, it has no special meaning in this string")]
                                )
                            
                            self._advance(2)
                            
                        # Escape `"`
                        case '"':
                            chars.append('"')
                            
                            # Warning de codigo basura al escapar una comilla que no necesita ser escapada
                            if start_quotes == "'":
                                span = Span(self._position, self._position + 2, self._file_map)
                                
                                self._diagnostic.emit(
                                    ErrorCode.W0001,
                                    { "quotes_used" : start_quotes,
                                      "quotes_escaped" : '"',
                                      "name_quote_used": "single" },
                                    [span],
                                    [(span, f'`\\"` here is unnecessary, it has no special meaning in this string')]
                                )
                            
                            self._advance(2)
                        
                        # Escape no soportado o invalido
                        case _:
                            span = Span(self._position, self._position + 2, self._file_map)
                            
                            self._diagnostic.emit(
                                ErrorCode.E0003,
                                { "escape" : f"{char}{self._peek(1)}" },
                                [span],
                                [(span, "this escape sequence is not supported in Zonetic")]
                            )
                            
                            self._advance(2)
                
                # Newline Literal
                case '\n':
                    chars.append('\n')
                    self._advance(1)
                
                # Tab Literal
                case '\t':
                    chars.append('\t')
                    self._advance(1)
                
                # Posible cierre de comillas
                case quotes if quotes == start_quotes:
                    success = True
                    self._advance(1)
                    break
                
                # Cualquier otro caracter
                case _:
                    chars.append(char)
                    self._advance(1)
        
        # Error de comillas no cerradas                
        if not success:
            self._diagnostic.emit(
                ErrorCode.E0004,
                { "quote" : start_quotes },
                [Span(start_position, self._position, self._file_map)],
                [(Span(self._position-1, self._position, self._file_map), "`{quote}` was expected here to close the string")]
            )
            return
            
        self._tokens._add(
            Token(
                TokenType.LITERAL_STRING,
                "".join(chars),
                Span(start_position, self._position, self._file_map)
                )
            )
 
            
    def scan_script(self) -> ListTokens:
        while not self._is_end():
            char = self._peek(0)
            
            match char:
                case ' ': 
                    self._advance(1)
                
                case '\n':
                    self._tokens._add(
                        Token(
                            TokenType.NEWLINE,
                            '\\n',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                
                case ';': 
                    self._tokens._add(
                        Token(
                            TokenType.SEMICOLON,
                            ';',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                
                case ':':
                    self._tokens._add(
                        Token(
                            TokenType.COLON,
                            ':',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                
                case ',':
                    self._tokens._add(
                        Token(
                            TokenType.COMMA,
                            ',',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case '(':
                    self._tokens._add(
                        Token(
                            TokenType.LPAREN,
                            '(',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case ')':
                    self._tokens._add(
                        Token(
                            TokenType.RPAREN,
                            ')',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case '{':
                    self._tokens._add(
                        Token(
                            TokenType.LBRACE,
                            '{',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case '}':
                    self._tokens._add(
                        Token(
                            TokenType.RBRACE,
                            '}',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case '[':
                    self._tokens._add(
                        Token(
                            TokenType.LBRACKET,
                            '[',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case ']':
                    self._tokens._add(
                        Token(
                            TokenType.RBRACKET,
                            ']',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                
                case '.':
                    self._tokens._add(
                        Token(
                            TokenType.DOT,
                            '.',
                            self._generic_span(1)
                        )
                    )
                    self._advance(1)
                    
                case '+':
                    self._scan_plus()
                    
                case '-':
                    self._scan_minus()
                    
                case '*':
                    self._scan_star()
                    
                case '/':
                    self._scan_slash()
                    
                case '%':
                    self._scan_percentage()
                    
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
                
                # TODO: COMMING SOON -> NOT Bit-Wise Operator
                case '~':
                    pass
                
                case _:
                    self._scan_other(char)
         
              
        self._tokens._add(
            Token(
                TokenType.EOF,
                "EOF",
                Span(self._code_len, self._code_len, self._file_map)
                )
            )
        
        return self._tokens


"""HAcer de ultimo:


"""
