from dataclasses import dataclass
from .error_code import ErrorCode
from .severity import Severity

@dataclass
class ErrorDefinition:
    error_code: ErrorCode
    severity: Severity 
    message: str
    note: str
    zonny: str