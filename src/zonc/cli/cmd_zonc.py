from zonc.location_file import FileMap
from zonc.zonc_errors import DiagnosticEngine
from zonc.scanner import Lexer, ListTokens
from zonc.syntatic_normalizer import TheNormalizer
from zonc.parser import Parser
from zonc.semantic import Semantic
from zonc.runtime import Interpreter, ZoneticRuntimeError
from zonc.utils.print_ast import print_ast
import pathlib
import os

if os.name == 'nt':
    CONFIG_FILE = pathlib.Path(os.environ.get('USERPROFILE', Path.home())) / ".zonconfig"
else:
    CONFIG_FILE = pathlib.Path.home() / ".zonconfig"

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

    return None # Si no se encuentra en ningún lado

def cmd_zon_run(rute_script: str = " ", cmd: str = "run", code_source: str = None):
    try:
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
        lexer = Lexer(code, tokens, diagnostic, file_map)
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
            print("Tokens of akon script\n")
            len_tokens = tokens._len()
            
            for idx in range(len_tokens):
                print(f"{idx} => {tokens._list[idx]}")
            
            return
        
        # Parser
        parser = Parser(tokens, diagnostic, file_map)
        root_node = parser.parse_program()
        
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
        
        # Print ast semanticamente correcto
        if cmd == "smt":
            print_ast(root_node)
            return
            
        # Interpreter
        interpreter = Interpreter(diagnostic)
        interpreter.execute(root_node)
            
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
    print("[zon info]: Zonetic Programmin Language")
    print("[ ^_^] <(\"Hi! I'm Zonny. I'm currently running on version 0.1.2 'The Struct Update'.")
    print("         I’m feeling quite organized today... I guess you could say I finally found some structure in my life!\")")


def cmd_zon_help(specific_command=None):
    commands = {
        "help":     "Show this help message or info about a specific command.",
        "r":        "Execute a Zonetic program file (.zon).",
        "vers":     "Show Zonny's greeting and the current version info.",
        "setpath":  "Set a global directory to look for .zon files.",
        "showpath": "Display the currently saved global path.",
        "clrpath":  "Clear the global path and return to system default.",
        "setfile":  "Create a file (and folders) and write code interactively.",
        "repl" :    "Use the repl mode of zonetic."
    }

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

        print(f"[zon info]: Writing to '{target_path.name}'. Type 'EOF' or Ctrl+D to save.")
        
    if mode == 1:
        print(f"[zon info]: Repl Mode. Type 'EOF' or Ctrl+D to end.")
    
    lines = []
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
                f.write("".join(lines))
        
            print(f"[zon info]: File forged successfully at: {target_path}")
            confirm = input(f"Do you want to run {target_path.name} now? (y/n): ").lower()
            
            if confirm in ['y', 'yes']:
                print(f"--- Executing {target_path.name} ---")
                cmd_zon_run(target_path)
            
        else:
            print("--- Executing ---")
            cmd_zon_run(code_source="".join(lines))
            
    except Exception as e:
        print(f"[zon error]: Failed to save file. {e}")