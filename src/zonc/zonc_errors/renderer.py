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
    
    
    def note_clean(self, text: str, num_line: int) -> str:
        if not text or not text.strip():
            return ""
        
        lines = text.splitlines()
        while lines and not lines[0].strip(): lines.pop(0)
        while lines and not lines[-1].strip(): lines.pop(-1)
        
        if not lines: return ""

        indent_base = len(lines[0]) - len(lines[0].lstrip())

        cleaned_lines = []
        for i, line in enumerate(lines):
            content = line[indent_base:] if len(line) >= indent_base else line.lstrip()
            
            if i == 0:
                cleaned_lines.append(content.rstrip())
            else:
                cleaned_lines.append((" " * (9 + num_line)) + content.lstrip())
                
        return "\n".join(cleaned_lines)

    
    def firm_call_clean(self, firm: str):
        new_firm = []
        for char in firm:
            if not char.isspace():
                new_firm.append(char)
        return "".join(new_firm)
    
    
    def format_traceback(self, stack: list, msg_rendered: list[str]):
        msg_rendered.append("Call Path:\n")
        msg_rendered.append(f" {self.firm_call_clean(stack[0].firm)}\n └─>")
        msg_rendered.append(f" {self.firm_call_clean(stack[1].firm)}\n     └─>")
        msg_rendered.append(f" {self.firm_call_clean(stack[2].firm)}\n         └─>")
        msg_rendered.append(f" {self.firm_call_clean(stack[3].firm)}\n             └─>")
        msg_rendered.append(f" {self.firm_call_clean(stack[4].firm)}\n                 └─>")
        msg_rendered.append(f" [ ... {stack[-1].depth - 4} identical calls hidden ... ]\n                     └─>")
        msg_rendered.append(f" {self.firm_call_clean(stack[-1].firm)}  ← crash happened here")
        
    def format_span_message(
        self,
        span_codes: list[Span],
        msg_rendered: list[str],
        span_error: list[tuple[Span, str]],
        args: dict[str, str]
        
    ) -> str:
        num_lines = []
        for i in range(len(span_codes)):
            num_lines.append(span_codes[i].line_end)
        
        num_lines.sort()
        size_line = len(str(num_lines[-1]))
        
        for i in range(len(span_codes)):
            # Lineas de todo el codigo de inicio a final
            lines = self.get_lines(span_codes[i].line_start, span_codes[i].line_end)
            
            if len(self.file_map.line_starts) != span_codes[i].line_end + 1:
                lines.pop()
            
            space_line = ' ' * size_line
            
            # Las tres formas de mostrar errores de zonetic
            if len(lines) == 1:
                msg_rendered.append(f"{span_codes[i].line_start} {' ' * (size_line - (len(str(span_codes[i].line_start))))}| {lines[0]}\n")
                paddings = " " * (span_error[i][0].column_start)
                pointers = "^" * (span_error[i][0].column_end - span_error[i][0].column_start)
                msg_rendered.append(f"{space_line} |{paddings}{pointers}")
                
                if not(span_error[i][1] is None):
                    msg_rendered.append(f"-- {span_error[i][1].format_map(args)}")
                
            elif len(lines) <= 6:
                count = 0
                for line in lines:
                    msg_rendered.append(f"{span_codes[i].line_start+count} {' ' * (size_line - (len(str(span_codes[i].line_start+count))))}| {line}\n")
                    count += 1
                    
                paddings = " " * (span_error[i][0].column_start)
                pointers = "^" * (span_error[i][0].column_end - span_error[i][0].column_start)
                msg_rendered.append(f"{space_line} |{paddings}{pointers}")
                
                if not(span_error[i][1] is None):
                    msg_rendered.append(f"-- {span_error[i][1].format_map(args)}")
            
            else:
                count = 0
                for line in lines:
                    msg_rendered.append(f"{span_codes[i].line_start+count} {' ' * (size_line - len(str(span_codes[i].line_start+count)))}| {line}\n")
                    
                    if count == 2:
                        break
                        
                    count += 1
                
                msg_rendered.append(f"{space_line} |\n{space_line} ...|\n{space_line} |\n")
                msg_rendered.append(f"{span_codes[i].line_end} | {lines[span_codes[i].line_end-span_codes[i].line_start]}\n")
                paddings = " " * (span_error[i][0].column_start)
                pointers = "^" * (span_error[i][0].column_end - span_error[i][0].column_start)
                msg_rendered.append(f"{space_line} |{paddings}{pointers}")
                
                if not(span_error[i][1] is None):
                    msg_rendered.append(f"-- {span_error[i][1].format_map(args)}")
            
            if i != len(span_codes)-1:
                msg_rendered.append(f"\n{space_line} |\n{space_line} ...|\n{space_line} |\n")

        return size_line
        
        
    def format_note_and_zonny(self, msg_rendered: list[str], space_line: str, err_def, args: dict[str, str]):
        msg_rendered.append(f"\n{space_line * ' '} |\n")
        if args is None:
            msg_rendered.append(f"{space_line * ' '} = note: {self.note_clean(err_def.note, space_line)}\n\n")
            msg_rendered.append(f"{err_def.zonny}")
        else:
            msg_rendered.append(f"{space_line * ' '} = note: {self.note_clean(err_def.note.format_map(args), space_line)}\n\n")
            msg_rendered.append(f"{err_def.zonny.format_map(args)}")
       
    
    def render(self, diag: Diagnostic, is_repeated: bool) -> str:
        err_def = diag.error_definition
        args = diag.args
        span_error = diag.span_errors
        name_file  = diag.name_file
        msg_rendered = []
        
        # Formateo de argumentos
        if not args is None:
            msg = err_def.message.format_map(args)
            
        else:
            msg = err_def.message
        
        # Header de error
        if err_def.severity == Severity.ERROR:
            msg_rendered.append(f"error[{err_def.error_code.name}]: {msg}\n")
        else:
            msg_rendered.append(f"warning[{err_def.error_code.name}]: {msg}\n")
            
        
        
        if diag.traceback:
            msg_rendered.append(f"--> {name_file}\n")
            self.format_traceback(diag.call_stack, msg_rendered)
            
            self.format_note_and_zonny(
                msg_rendered,
                0,
                err_def,
                args
            )

        else:
            msg_rendered.append(f"--> {name_file}:{span_error[0][0].line_start}:{span_error[0][0].column_start}\n")
            space_line = self.format_span_message(
                diag.span_code,
                msg_rendered,
                diag.span_errors,
                args
            )
            
            if not is_repeated:
                self.format_note_and_zonny(
                    msg_rendered,
                    space_line,
                    err_def,
                    args
                )
                
                
        return "".join(msg_rendered)