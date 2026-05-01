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
        ErrorCode.E0006 : 0,
        ErrorCode.E0007 : 0,
        ErrorCode.E0008 : 0,
        ErrorCode.E0009 : 0,
        ErrorCode.E0010 : 0,
        ErrorCode.E0011 : 0,
        ErrorCode.E0012 : 0,
        
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
        ErrorCode.E2012 : 0,
        ErrorCode.E2013 : 0,
        ErrorCode.E2014 : 0,
        ErrorCode.E2015 : 0,
        ErrorCode.E2016 : 0,
        ErrorCode.E2017 : 0,
        ErrorCode.E2018 : 0,
        ErrorCode.E2019 : 0,
        ErrorCode.E2020 : 0,
        ErrorCode.E2021 : 0,
        ErrorCode.E2022 : 0,
        ErrorCode.E2023 : 0,
        ErrorCode.E2024 : 0,
        ErrorCode.E2025 : 0,
        ErrorCode.E2026 : 0,
        ErrorCode.E2027 : 0,
        ErrorCode.E2028 : 0,
        ErrorCode.E2029 : 0,
        ErrorCode.E2030 : 0,
        ErrorCode.E2031 : 0,
        ErrorCode.E2032 : 0,
        
        ErrorCode.W2001 : 0,
        
        ErrorCode.E3001 : 0,
        ErrorCode.E3002 : 0,
        ErrorCode.E3003 : 0,
        ErrorCode.E3004 : 0,
        ErrorCode.E3005 : 0,
        ErrorCode.E3006 : 0,
        ErrorCode.E3007 : 0,
        ErrorCode.E3008 : 0,
        ErrorCode.E3009 : 0,
        ErrorCode.E3010 : 0,
        ErrorCode.E3011 : 0,
        ErrorCode.E3012 : 0,
        ErrorCode.E3013 : 0,
        ErrorCode.E3014 : 0,
        ErrorCode.E3015 : 0,
        ErrorCode.E3016 : 0,
        ErrorCode.E3017 : 0,
        ErrorCode.E3018 : 0,
        ErrorCode.E3019 : 0,
        ErrorCode.E3020 : 0,
        ErrorCode.E3021 : 0,
        ErrorCode.E3022 : 0,
        ErrorCode.E3023 : 0,
        ErrorCode.E3024 : 0,
        ErrorCode.E3025 : 0,
        ErrorCode.E3026 : 0,
        ErrorCode.E3027 : 0,
        ErrorCode.E3028 : 0,
        ErrorCode.E3029 : 0,
        ErrorCode.E3030 : 0,
        ErrorCode.E3031 : 0,
        ErrorCode.E3032 : 0,
        ErrorCode.E3033 : 0,
        ErrorCode.E3034 : 0,
        ErrorCode.E3035 : 0,
        ErrorCode.E3036 : 0,
        ErrorCode.E3037 : 0,
        ErrorCode.E3038 : 0,
        ErrorCode.E3039 : 0,
        ErrorCode.E3040 : 0,
        ErrorCode.E3041 : 0,
        ErrorCode.E3042 : 0,
        ErrorCode.E3043 : 0,
        ErrorCode.E3044 : 0,
        ErrorCode.E3045 : 0,
        ErrorCode.E3046 : 0,
        
        ErrorCode.W3001 : 0,
        ErrorCode.W3002 : 0,
        ErrorCode.W3003 : 0,
        ErrorCode.W3004 : 0,
        ErrorCode.W3005 : 0,
        ErrorCode.W3006 : 0,
        
        ErrorCode.E4001: 0,
        ErrorCode.E4002: 0,
        
        ErrorCode.E5001: 0,
        ErrorCode.E5002: 0,
        ErrorCode.E5003: 0,
        ErrorCode.E5004: 0,
        ErrorCode.E5005: 0,
        
        ErrorCode.W5001: 0,
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
        span_code: list[Span] | None,
        span_error: list[tuple[Span, str]] | None,
        traceback: bool = False,
        call_stack: list | None = None
    ) -> None:
        if error_code in ERROR_REGISTRY:
            err_def = ERROR_REGISTRY[error_code]
            if traceback:
                self.errors.append(
                    Diagnostic(
                        err_def,
                        args,
                        None,
                        span_error,
                        True,
                        call_stack,
                        self.name_file
                    )
                )
            
            else:
                self.errors.append(
                    Diagnostic(
                        err_def,
                        args,
                        span_code,
                        span_error,
                        False,
                        None,
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
        
        self.errors.sort(key=lambda e: e.span_errors[0][0].start)
        
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
                print(f"... and {self.count_errors - count_err} more errors, plus {self.count_warnings - count_warn} more warnings; I recommend resolving errors from the top down, sometimes there are cascading errors.")
                break
            


