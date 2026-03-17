from .error_registry import ERROR_REGISTRY
from .error_code import ErrorCode
from .severity import Severity
from zonc.location_file import Span
from .diagnostic import Diagnostic
from .renderer import DiagnosticRenderer

class DiagnosticEngine:
    ERROR_OCCURRENCE = {
        ErrorCode.E0001 : 0,
        ErrorCode.E0002 : 0,
        ErrorCode.E0003 : 0,
        ErrorCode.E0004 : 0,
        ErrorCode.E0005 : 0,
        ErrorCode.W0001 : 0,
        
        ErrorCode.E1001 : 0,
        ErrorCode.E1002 : 0,
        
        ErrorCode.E2001 : 0,
        ErrorCode.E2002 : 0,
        ErrorCode.E2003 : 0,
        ErrorCode.E2004 : 0,
        ErrorCode.E2005 : 0,
        ErrorCode.E2006 : 0,
        ErrorCode.E2007 : 0,
        ErrorCode.E2008 : 0,
        ErrorCode.E2009 : 0,
        ErrorCode.E2010 : 0,
        ErrorCode.E2011 : 0,
        ErrorCode.W2001 : 0,
        
        ErrorCode.E3001 : 0,
        ErrorCode.E3002 : 0,
        ErrorCode.E3003 : 0,
        ErrorCode.E3004 : 0,
        ErrorCode.E3005 : 0,
        ErrorCode.E3006 : 0,
        ErrorCode.W3001 : 0,
    }

    
    def __init__(self, name_file: str, code: str, file_map) -> None:
        self.errors: list[Diagnostic] = []
        self.renderer = DiagnosticRenderer(code, file_map)
        self.name_file = name_file
        self.count_errors = 0
        self.count_warnings = 0
    
    
    def emit(
        self,
        error_code: ErrorCode,
        args: dict[str, str] | None,
        span_code: Span,
        span_error: tuple[Span, str | None],
    ) -> None:
        if error_code in ERROR_REGISTRY:
            err_def = ERROR_REGISTRY[error_code]
            self.errors.append(
                Diagnostic(
                    err_def,
                    args,
                    span_code,
                    span_error,
                    self.name_file,
                )
            )
            
            if err_def.severity == Severity.ERROR:
                self.count_errors += 1
            elif err_def.severity == Severity.WARNING:
                self.count_warnings += 1
                
        else:
            print(f"Internal Error: {error_code} code not exist in the Zonetic Error Registry.")
            
            
    def has_errors(self) -> bool:
        return self.count_errors > 0
    
    
    def clear_engine(self) -> None:
        self.errors.clear()
        for k in self.ERROR_OCCURRENCE:
            self.ERROR_OCCURRENCE[k] = 0
        
            
    def display(self) -> None:
        count_err = 0
        count_warn = 0
        
        self.errors.sort(key=lambda e: e.span_code.start)
        
        for diag in self.errors:
            self.ERROR_OCCURRENCE[diag.error_definition.error_code] += 1
            
            if self.ERROR_OCCURRENCE[diag.error_definition.error_code] > 1:
                msg_formated = self.renderer.render(diag, True)
            else:
                msg_formated = self.renderer.render(diag, False)
                
            print(msg_formated)
            print()
            print()
            
            if diag.error_definition.severity == Severity.ERROR:
                count_err += 1
            else:
                count_warn += 1
            
            if count_err + count_warn == 10:
                print(f"... and {self.count_errors - count_err} more errors, plus {self.count_warnings - count_warn} more warnings; resolve the ones above to see the remaining ones.")
                break
            


