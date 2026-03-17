from zonc.scanner import Token, TokenType, ListTokens
from zonc.zonc_errors import DiagnosticEngine, ErrorCode
from zonc.location_file import Span, FileMap

class TheNormalizer:
    tokens_valids = [
        TokenType.LITERAL_NUMBER,
        TokenType.LITERAL_STRING,
        TokenType.LITERAL_IDENT,
        TokenType.LITERAL_TRUE,
        TokenType.LITERAL_FALSE,
        TokenType.RPAREN,
        TokenType.KEYWORD_CONTINUE,
        TokenType.KEYWORD_BREAK,
        TokenType.RBRACE,
        TokenType.KEYWORD_BOOL,
        TokenType.KEYWORD_FLOAT,
        TokenType.KEYWORD_INT,
        TokenType.KEYWORD_STRING,
        TokenType.KEYWORD_GIVE
    ]
    
    def __init__(self, tokens: ListTokens, diag: DiagnosticEngine, file_map: FileMap):
        self.tokens = tokens
        self.position = 0
        self.diag = diag
        self.file_map = file_map

        
    def is_valid(self, type: TokenType) -> bool:
        return type in self.tokens_valids
        
        
    def is_end(self) -> bool:
        return self.tokens._peek(self.position)._type == TokenType.EOF
    
    
    def peek_type(self, step: int) -> TokenType:
        if self.position + step > self.tokens._len() or self.position + step < 0:
            return TokenType.NONE
        
        return self.tokens._peek(self.position + step)._type
    
    
    def line(self) -> int:
        return self.tokens._peek(self.position)._span.line_start
        
        
    def column(self) -> int:
        return self.tokens._peek(self.position)._span.column_start
        
        
    def normalizer(self) -> ListTokens:
        depth = 0
        semicolon_mode = False
        verified = False
        
        while not self.is_end():
            if self.peek_type(0) == TokenType.NEWLINE:
                
                if not depth > 0:
                    
                    if self.is_valid(self.peek_type(-1)) and self.peek_type(1) != TokenType.LBRACE:
                        span = self.tokens._peek(self.position)._span
                        
                        if verified and semicolon_mode:
                            
                            self.diag.emit(
                                ErrorCode.E1001,
                                { "mode_tr" : "semicolons",
                                  "used_tr" : "newline" },
                                span,
                                (span, "unexpected newline, this file uses semicolons as statement terminators")  
                            )
                            self.position += 1
                            continue
                        
                        self.tokens._replace(
                            self.position,
                            Token(
                                TokenType.SEMICOLON,
                                ';',
                                span
                            )
                        )
                        
                        if not verified:
                            verified = True
                        
                        self.position += 1
                        
                    else:
                        self.tokens._del(self.position)
                        
                else:
                    self.tokens._del(self.position)
            
            
            elif self.peek_type(0) == TokenType.LPAREN:
                depth += 1
                self.position += 1
            
            elif (depth > 0) and (self.peek_type(0) == TokenType.RPAREN):
                depth -= 1
                self.position += 1
            
            elif (self.peek_type(0) == TokenType.SEMICOLON):
                span = self.tokens._peek(self.position)._span
                
                if depth > 0 or not self.is_valid(self.peek_type(-1)):
                    self.diag.emit(
                        ErrorCode.E1002,
                        None,
                        span,
                        (span, "`;` is not valid here, no statement was opened before this")    
                    )
                
                elif verified and not semicolon_mode:
                    self.diag.emit(
                        ErrorCode.E1001,
                        { "mode_tr" : "newlines",
                          "used_tr" : "semicolon" },
                        span,
                        (span, "unexpected `;`, this file uses newlines as statement terminators")
                    )
                
                else:
                    if not verified:
                        semicolon_mode = True
                        verified = True
                
                self.position += 1

            else:
                self.position += 1
                        
        
        
        if not(semicolon_mode) and self.is_valid(self.peek_type(-1)):
            span = self.tokens._peek(self.position)._span
            
            self.tokens._add(Token(TokenType.EOF, "", Span(span.start+1, span.end+1, self.file_map)))
            self.tokens._replace(self.position, Token(TokenType.SEMICOLON, ';', Span(span.start, span.end+1, self.file_map)))
            
        return self.tokens