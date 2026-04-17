from zonc.location_file import FileMap
from zonc.zonc_errors import DiagnosticEngine
from zonc.scanner import Lexer, ListTokens, TokenType
from zonc.syntatic_normalizer import TheNormalizer
from zonc.parser import Parser
from zonc.semantic import Semantic
from zonc.runtime import Interpreter, ZoneticRuntimeError
from zonc.utils import print_ast, print_tokens
import pathlib
import os
from zonc.utils import Chronometer
import readline
import atexit

if os.name == 'nt':
    CONFIG_FILE = pathlib.Path(os.environ.get('USERPROFILE', pathlib.Path.home())) / ".zonconfig"
else:
    CONFIG_FILE = pathlib.Path.home() / ".zonconfig"
    
KEYWORDS = {
        "int": TokenType.KEYWORD_INT,
        "float": TokenType.KEYWORD_FLOAT,
        "string": TokenType.KEYWORD_STRING,
        "bool": TokenType.KEYWORD_BOOL,
        "mut": TokenType.KEYWORD_MUT,
        "inmut": TokenType.KEYWORD_INMUT,
        "if": TokenType.KEYWORD_IF,
        "elif": TokenType.KEYWORD_ELIF,
        "else": TokenType.KEYWORD_ELSE,
        "while": TokenType.KEYWORD_WHILE,
        "infinity": TokenType.KEYWORD_INFINITY,
        "continue": TokenType.KEYWORD_CONTINUE,
        "break": TokenType.KEYWORD_BREAK,
        "and": TokenType.GATE_AND,
        "or": TokenType.GATE_OR,
        "not": TokenType.GATE_NOT,
        "true" : TokenType.LITERAL_TRUE,
        "false" : TokenType.LITERAL_FALSE,
        "give" : TokenType.KEYWORD_GIVE,
        "func" : TokenType.KEYWORD_FUNC,
        "void" : TokenType.KEYWORD_VOID,
        "return" : TokenType.KEYWORD_RETURN,
        "struct" : TokenType.KEYWORD_STRUCT
    }

def get_target_path(filename):
    local_file = pathlib.Path(filename)
    if local_file.exists():
        return local_file

    # Si no existe localmente, buscamos en el config
    if CONFIG_FILE.exists() and CONFIG_FILE.stat().st_size > 0:
        with open(CONFIG_FILE, "r") as f:
            global_dir = pathlib.Path(f.read().strip())
            global_file = global_dir / filename
            if global_file.exists():
                return global_file

    return None

def cmd_zon_run(rute_script: str = " ", cmd: str = "run", code_source: str = None):
    try:
        chrono_compiler = Chronometer()
        chrono_compiler.start()
        
        code = " "
        name_file = " "
        
        if code_source is None:
            path_name = get_target_path(rute_script)
            
            if path_name is None:
                print("[zon error]: The path or file could not be found.")
                print("-- Double-check your spelling and ensure the file exists in that directory.")
                return
            
            if not path_name.is_file():
                print(f"[zon error]: '{path_name.name}' is not a file.")
                print("-- You provided a directory path. Please specify the exact .zon file you want to run.")
                return
            
            if path_name.suffix != ".zon":
                print(f"[zon error]: '{path_name.name}' is not a Zonetic file.")
                print("-- The engine only accepts files with the .zon extension. Please check your file type.")
                return
            
            with open(path_name, "r", newline=None) as file_zon:
                code = file_zon.read()
                
            name_file = path_name.name
        
        else:
            code = code_source
            name_file = "repl"
            
    
        # File Map
        file_map = FileMap(code) 

        # Diagnostic Engine
        diagnostic = DiagnosticEngine(name_file, code, file_map)
        
        # List Token
        tokens = ListTokens()
        
        # Lexer
        lexer = Lexer(code, tokens, diagnostic, file_map, KEYWORDS)
        tokens = lexer.scan_script()
        
        if diagnostic.has_errors():
            diagnostic.display()
            diagnostic.clear_engine()
            return
        
        if tokens._len() < 2:
            print(f"Zonetic Compiler Message: The file `{name_file}` has nothing important to parse")
            return
        
        # Normalizer
        the_normalizer = TheNormalizer(tokens, diagnostic, file_map)
        tokens = the_normalizer.normalizer()
        
        if diagnostic.has_errors():
            diagnostic.display()
            diagnostic.clear_engine()
            return
        
        # Print Tokens
        if cmd == "token":
            print_tokens(tokens._list)
            return
        
        # Parser
        parser = Parser(tokens, diagnostic, file_map)
        root_node = parser.parse_program(name_file)
        
        if diagnostic.has_errors():
            diagnostic.display()
            diagnostic.clear_engine()
            return
        
        # Print Ast
        if cmd == "ast":
            print_ast(root_node)
            return
        
        # Semantic
        semantic_checker = Semantic(diagnostic, file_map)
        semantic_checker.check_ast(root_node, False)
        
        if diagnostic.has_errors():
            diagnostic.display()
            diagnostic.clear_engine()
            return
        
        chrono_compiler.stop()
            
        # Interpreter
        chrono_interpreter = Chronometer()
        chrono_interpreter.start() 
        interpreter = Interpreter(diagnostic)
        interpreter.execute(root_node)
        chrono_interpreter.stop()
        
        time_total = Chronometer()
        time_total.start_time = chrono_compiler.start_time
        time_total.stop_time = chrono_interpreter.stop_time
        
        if diagnostic.count_warnings > 0:
            print("-"*80)
            print(f"[ SUCCESS ] Compiler: {chrono_compiler.format()} | Runtime: {chrono_interpreter.format()} | Total: {time_total.format()}")
            print(f"[ ^_^] <(\"Done! I found {diagnostic.count_warnings} warnings, but your code is safe. Check them to keep the Forge clean!\")")
        else:
            print("-"*80)
            print(f"[ MASSIVE SUCCESS ] Compiler: {chrono_compiler.format()} | Runtime: {chrono_interpreter.format()} | Total: {time_total.format()}")
            print(f"[ ⌐■_■]b <(\"Epic execution, bro. Your logic is as sharp as a Katana!\")")
            
        
            
    except ZoneticRuntimeError as e:
        diagnostic.emit(
            e.error_code,
            e.arg,
            e.span_code,
            e.span_error,
            e.traceback,
            e.call_stack
        )
        diagnostic.display()
        diagnostic.clear_engine()
        return
    
    except KeyboardInterrupt:
        print("""\n[zon note]: program interrupted by user.
-- Did an infinite loop get you? Check your loops and conditions.""")
    
   
def cmd_zon_version():
    print("[zon info]: Zonetic Programming Language")
    print("[ ^_^] <(\"Hi! I'm Zonny. I'm currently running on version 0.1.5 'The Install Auto Windows Update'.")
    print("         I've officially learned to hop between Android, Linux, and Windows!")
    print("         I’m like a digital nomad, but without the expensive coffee...\")")
    
def cmd_zon_help(specific_command=None, commands=None):
    if specific_command:
        if specific_command in commands:
            if specific_command == "help":
                print("[zon info]: Help about... help?")
                print("[ o_O] <(\"Yo Dawg, I heard you like help, so I put some help") 
                print("         in your help so you can get help while you help!\")\n")
            
            print(f"Usage: zon {specific_command} [arguments]")
            print(f"Description: {commands[specific_command]}")
        else:
            print(f"[zon error]: Command '{specific_command}' not found in help.")
            
        return
    
    print("Zonetic Programming Language - Usage: zon <command> [arguments]\n")
    print("Available Commands:")
    
    for cmd in sorted(commands.keys()):
        explanation = commands[cmd]
        print(f"  {cmd:<10} {explanation}")

    print("\nUse 'zon help <command>' for more details on a specific action.")
    
def cmd_zon_set_path(args):
    new_path = pathlib.Path(args).resolve()
    print(new_path)
    
    if new_path.is_file():
        print("[zon error]: The path provided is a file, not a directory.")
        print("-- setpath expects a folder where your scripts live. Please provide a directory path.")
        return
    
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(str(new_path))
        print(f"[zon info]: Global path set to: {new_path}")
    except Exception as e:
        print(f"[zon error]: Could not write config file. {e}")
        
def cmd_zon_show_path():
    if not CONFIG_FILE.exists() or CONFIG_FILE.stat().st_size == 0:
        print("[zon info]: No global path is currently set.")
        return

    with open(CONFIG_FILE, "r") as f:
        print(f"[zon info]: Current global path: {f.read()}")
        
def cmd_zon_clear_path():
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write("")
        print("[zon info]: Global path cleared.")
        print("-- Zonetic will now use the default system path.")
    except Exception as e:
        print(f"[zon error]: Could not clear config file. {e}")

def cmd_zon_set_file(args=None, mode=0):
    if mode == 0:
        target_path = pathlib.Path(args)
    
        try:
            if not target_path.parent.exists():
                print(f"[zon info]: Creating directory structure: {target_path.parent}")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            print(f"[zon error]: Could not create directories. {e}")
            return
    
        if target_path.suffix != ".zon":
            print("[zon error]: Invalid file extension for Zonetic.")
            print("-- The forge only works with .zon files. Please ensure your path or filename ends with the correct extension.")
            return

    
    short_eof = ""
    if os.name == "nt":
        short_eof = "Ctrl+Z and Enter"
    else:
        short_eof = "Ctrl+D"
    
    if mode == 1:    
        print(f"[zon info]: Repl Mode. Type 'EOF' or {short_eof} to end.")
    else:
        print(f"[zon info]: Writing to '{target_path.name}'. Type 'EOF' or {short_eof} to save.")
    
    lines = []
    not_readline = False
    if os.name != "nt":
        try:
            history_file = os.path.expanduser("~/.zonhistoryrepl")
            if not os.path.exists(history_file):
                try:
                    with open(history_file, 'a') as f:
                        os.utime(history_file, None)
                except OSError:
                    print("[ X_X] <(\"Warning: Cannot write to history file. Your session won't be saved.\")")
                    pass
                
            if os.path.exists(history_file):
                try:
                    readline.read_history_file(history_file)
                except FileNotFoundError:
                    pass
                
            readline.set_history_length(500)
            atexit.register(readline.write_history_file, history_file)
            readline.parse_and_bind("set editing-mode emacs")
            keywords = ["EOF"]
            for key in KEYWORDS:
                keywords.append(key)
    
            def completer(text, state):
                options = [k for k in keywords if k.startswith(text)]
                if state < len(options):
                    return options[state]
                else:
                    return None

            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")
            
            try:
                while True:
                    line = input(">> ").rstrip('\r')
                    if line.strip().upper() == "EOF":
                        break
                    lines.append(line)
                    readline.add_history(line)
            except EOFError:
                print("\n")
                pass
            
            except KeyboardInterrupt:
                print("[zon info]: Program execution interrupted.")
                if mode == 0:
                    print("-- The forge was cooled down too early. The file was not saved.")    
                
                return
            
        except ImportError:
            not_readline = True
    
    if os.name == "nt" or not_readline:
        try:
            while True:
                line = input(">> ").rstrip('\r')
                if line.strip().upper() == "EOF":
                    break
                lines.append(line)
        except EOFError:
            print("\n")
            pass
        
        except KeyboardInterrupt:
            print("[zon info]: Program execution interrupted.")
            if mode == 0:
                print("-- The forge was cooled down too early. The file was not saved.")    
            
            return

    if not lines:
        print("[zon note]: No code entered. Operation cancelled.")
        return

    try:
        if mode == 0:
            with open(target_path, "w", encoding="utf-8", newline='\n') as f:
                f.write("\n".join(lines))
        
            print(f"[zon info]: File forged successfully at: {target_path}")
            confirm = input(f"Do you want to run {target_path.name} now? (y/n): ").lower()
            
            while confirm not in ['y', "yes", 'n', "no"]:
                confirm = input(f"Do you want to run {target_path.name} now? (y/n): ").lower()
            
            if confirm in ['y', 'yes']:
                print(f"--- Executing {target_path.name} ---")
                cmd_zon_run(target_path)
            
        else:
            print("--- Executing ---")
            cmd_zon_run(code_source="\n".join(lines))
            
    except Exception as e:
        print(f"[zon error]: Failed to save file. {e}")
