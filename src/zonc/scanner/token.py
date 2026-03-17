from dataclasses import dataclass
from zonc.location_file import Span
from .tokentype import TokenType



@dataclass
class Token:
    _type: TokenType
    _value: str
    _span: Span
    
    def __repr__(self):
        return f"{__class__.__name__}(type={self._type}, value='{self._value}', start={self._span.start}, end={self._span.end})"