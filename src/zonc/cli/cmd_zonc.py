from zonc.location_file import FileMap
from zonc.zonc_errors import DiagnosticEngine
from zonc.scanner import Lexer, ListTokens, TokenType
from zonc.syntatic_normalizer import TheNormalizer
from zonc.parser import Parser
from zonc.semantic import Semantic
from zonc.optimization import *
from zonc.runtime import Interpreter, ZoneticRuntimeError
from zonc.utils import print_ast, print_tokens
import pathlib
import os
from zonc.utils import Chronometer
from zonc.bytecodegen import *
import traceback

if os.name == 'nt':
    CONFIG_FILE = pathlib.Path(os.environ.get('USERPROFILE', pathlib.Path.home())) / ".zonconfig"
else:
    import readline
    import atexit
    CONFIG_FILE = pathlib.Path.home() / ".zonconfig"
    
KEYWORDS = {
        "int64": TokenType.KEYWORD_INT64,
        "int32": TokenType.KEYWORD_INT32,
        "float": TokenType.KEYWORD_FLOAT,
        "double": TokenType.KEYWORD_DOUBLE,
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
            print(f"[zon note]: The file `{name_file}` has nothing important to parse")
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

def cmd_zon_compile(rute_script: str = " ", code_source: str = None, direct_zbc: str = None):
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
        print(f"[zon note]: The file `{name_file}` has nothing important to parse")
        return
    
    # Normalizer
    the_normalizer = TheNormalizer(tokens, diagnostic, file_map)
    tokens = the_normalizer.normalizer()
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
        return
    # Parser
    parser = Parser(tokens, diagnostic, file_map)
    root_node = parser.parse_program(name_file)
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
        return
    
    # Semantic
    semantic_checker = Semantic(diagnostic, file_map)
    semantic_checker.check_ast(root_node, False)
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
        return
    
    constant_folding = ConstantFolding(diagnostic)
    constant_folding.visit_Program(root_node)
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
        return
    
    dce = DeadCodeElimination()
    dce.eliminate_in_program(root_node)
            
    em = Emitter()
    for stmt in root_node.stmts:
        em.generate_stmt(stmt)
        
    em.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, 93)
    em.emit_ecall()
    
    if direct_zbc is None:
        em.save(path_name.with_suffix(".zbc"))
    else:
        em.save(direct_zbc)
   
def cmd_zon_version():
    print("[zon info]: Zonetic Programming Language")
    print("[ ^_^] <(\"Hi! I'm Zonny. I'm currently running on version 0.1.5 'The Install Auto Windows Update'.")
    print("         I've officially learned to hop between Android, Linux, and Windows!")
    print("         I’m like a digital nomad, but without the expensive coffee...\")")
    
def cmd_zon_help(command_name: str = None, commands=None):
    if command_name and command_name in commands:
        cmd = commands[command_name]
        if command_name == "help":
            print("HELP: Area 'help'?")
        else:
            print(f"HELP: Area '{cmd.area}'")
        
        print(f"Usage: {cmd.usage}\n")
        
        print(f"Description:\n{cmd.summary}\n")

        if hasattr(cmd, 'args') and cmd.args:
            print("Arguments:")
            for arg in cmd.args:
                print(f"    {arg.name:<14} {arg.description}")
            print()

        if hasattr(cmd, 'flags') and cmd.flags:
            print("Flags:")
            for flag in cmd.flags:
                print(f"    {flag.name:<18} {flag.description}")
            print()
            
        if command_name == "help":
            print("[ o_O] <(\"Yo Dawg, I heard you like help, so I put some help") 
            print("         in your help so you can get help while you help!\")\n")
            
        return
    
    elif command_name and command_name not in commands:
        print(f"[zon error]: Command '{command_name}' not found in help.")
        return

    print("Zonetic Programming Language")
    print("Usage: zon <area> [flags] [arguments]\n")

    categories = {
        "exe": "Execution",
        "manag": "Management",
        "sys": "System"
    }

    for cat_key, cat_name in categories.items():
        print(f"{cat_name}:")
        for key, cmd in commands.items():
            if cmd.category == cat_key:
                print(f"  {cmd.area:<10} {cmd.summary}")
        print()

    print("Use 'zon help [area]' to see all available flags and usage examples.")
    
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
    if mode in [0, 4]:
        target_path = pathlib.Path(args[0])
    
        try:
            if not target_path.parent.exists():
                print(f"[zon info]: Creating directory structure: {target_path.parent}")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            print(f"[zon error]: Could not create directories. {e}")
            return

        if mode == 0 and target_path.suffix != ".zon":
            print("[zon error]: Invalid file extension for Zonetic.")
            print("-- The forge only works with .zon files. Please ensure your path or filename ends with the correct extension.")
            return

        if mode == 4 and target_path.suffix != ".zbc":
            print("[zon error]: Invalid file extension for Zonetic.")
            print("-- The forge only works with .zbc files. Please ensure your path or filename ends with the correct extension.")
            return

    
    short_eof = ""
    if os.name == "nt":
        short_eof = "Ctrl+Z and Enter"
    else:
        short_eof = "Ctrl+D"
        
    endkey = ""
    if mode in [0, 4, 3]:
        endkey = args[1]
    else:
        endkey = args[0]
    
    if mode in [1, 3]:    
        print(f"[zon info]: Repl Mode. Type '{endkey}' or {short_eof} to end.")
    else:
        print(f"[zon info]: Writing to '{target_path.name}'. Type '{endkey}' or {short_eof} to save.")
    
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
                    if line.strip().upper() == endkey:
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
                if line.strip().upper() == endkey:
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
        if mode in [0, 4]:
            with open(target_path.with_suffix(".zon"), "w", encoding="utf-8", newline='\n') as f:
                f.write("\n".join(lines))

            if mode == 4:
                cmd_zon_compile(target_path.with_suffix(".zon"))
                
            print(f"[zon info]: File forged successfully at: {target_path}")
            if mode == 0:
                print("WARNING: old interpreter, It may not have all the new features.")
                confirm = input(f"Do you want to run {target_path.name} in legacy interpreter now? (y/n): ").lower()
                
                while confirm not in ['y', "yes", 'n', "no"]:
                    confirm = input(f"Do you want to run {target_path.name} now? (y/n): ").lower()
                
                if confirm in ['y', 'yes']:
                    print(f"--- Executing {target_path.name} ---")
                    cmd_zon_run(target_path)

            
        else:
            print("--- Executing ---")
            if mode == 1:
                cmd_zon_run(code_source="\n".join(lines))
            else:
                cmd_zon_compile(code_source="\n".join(lines), direct_zbc=args[0])
            
            
    except Exception as e:
        traceback.print_exc()
        print(f"[zon error]: Failed to save file. {e.with_traceback}")