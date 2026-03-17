from .severity import Severity
from zonc.location_file import FileMap
from zonc.location_file import Span
from .diagnostic import Diagnostic

class DiagnosticRenderer:
    def __init__(self, code: str, file_map: FileMap):
        self.code = code
        self.file_map = file_map
    
    def get_lines(self, line_start: int, line_end: int) -> list[str]:
        return self.code[self.file_map.line_starts[line_start-1] : self.file_map.line_starts[line_end]].split('\n')
    
    def render(self, diag: Diagnostic, is_repeated: bool) -> str:
        err_def = diag.error_definition
        args = diag.args
        span_code: Span = diag.span_code
        span_error: tuple[Span, str | None] = diag.span_error
        name_file  = diag.name_file
        msg_rendered = []
        
        # Formateo de argumentos
        if not args is None:
            msg = err_def.message.format_map(args)
            
        else:
            msg = err_def.message
        
        # Header de error
        if err_def.severity == Severity.ERROR:
            msg_rendered.append(f"error[{err_def.error_code.name}]: {msg}\n--> {name_file}:{span_error[0].line_start}:{span_error[0].column_start}\n")
        else:
            msg_rendered.append(f"warning[{err_def.error_code.name}]: {msg}\n--> {name_file}:{span_error[0].line_end}:{span_error[0].column_end}\n")
        
        # Lineas de todo el codigo de inicio a final
        lines = self.get_lines(span_code.line_start, span_code.line_end)
        
        if len(self.file_map.line_starts) != span_code.line_end + 1:
            lines.pop()
        
        # Las tres formas de mostrar errores de zonetic
        if len(lines) == 1:
            msg_rendered.append(f"{span_code.line_start} | {lines[0]}\n")
            size_line = ' ' * len(str(span_code.line_start))
            paddings = " " * (span_error[0].column_start)
            pointers = "^" * (span_error[0].column_end - span_error[0].column_start)
            msg_rendered.append(f"{size_line} |{paddings}{pointers}")
            
            if not(span_error[1] is None):
                msg_rendered.append(f"-- {span_error[1].format_map(args)}")
            
            if not is_repeated:
                msg_rendered.append(f"\n{size_line} |\n")
                msg_rendered.append(f"{size_line} = note: {err_def.note.format_map(args)}\n\n")
                msg_rendered.append(f"{err_def.zonny.format_map(args)}")
        
        elif len(lines) <= 6:
            count = 0
            size_line = 0
            for line in lines:
                msg_rendered.append(f"{span_code.line_start+count} | {line}\n")
                count += 1
                size_line = len(str(span_code.line_start))
            size_line = f"{' ' * size_line}"
                
            
            paddings = " " * (span_error[0].column_start)
            pointers = "^" * (span_error[0].column_end - span_error[0].column_start)
            msg_rendered.append(f"{size_line} |{paddings}{pointers}")
            
            if not(span_error[1] is None):
                msg_rendered.append(f"-- {span_error[1].format_map(args)}")
            
            if not is_repeated:
                msg_rendered.append(f"\n{size_line} |\n")
                msg_rendered.append(f"{size_line} = note: {err_def.note.format_map(args)}\n\n")
                msg_rendered.append(f"{err_def.zonny.format_map(args)}")
        
        else:
            count = 0
            size_line = len(str(span_code.line_end))
            for line in lines:
                msg_rendered.append(f"{' ' * (size_line - len(str(span_code.line_start)))}{span_code.line_start+count} | {line}\n")
                
                if count == 2:
                    break
                    
                count += 1
            
            size_line = ' ' * size_line
            
            msg_rendered.append(f"{size_line}...|\n")
            msg_rendered.append(f"{span_code.line_end} | {lines[span_code.line_end-1]}\n")
            paddings = " " * (span_error[0].column_end)
            pointers = "^" * (span_error[0].column_end - span_error[0].column_start)
            msg_rendered.append(f"{size_line} |{paddings}{pointers}")
            
            if not(span_error[1] is None):
                msg_rendered.append(f"-- {span_error[1].format_map(args)}")
            
            if not is_repeated:
                msg_rendered.append(f"\n{size_line} |\n")
                msg_rendered.append(f"{size_line} = note: {err_def.note.format_map(args)}\n\n")
                msg_rendered.append(f"{err_def.zonny.format_map(args)}")
        
        return "".join(msg_rendered)