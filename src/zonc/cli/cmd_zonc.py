from zonc.location_file import FileMap
from zonc.zonc_errors import DiagnosticEngine
from zonc.scanner import Lexer, ListTokens
from zonc.syntatic_normalizer import TheNormalizer
from zonc.parser import Parser
from zonc.semantic import Semantic
from zonc.runtime import Interpreter
from zonc.utils.print_ast import print_ast
import pathlib

def cmd_akorn_run(rute_script: str, cmd: str = "run"):
    ruta = pathlib.Path(rute_script)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.touch(exist_ok=True)
        
    # Code Akon
    with open(ruta, "r") as file_zon:
        code = file_zon.read()
    
    # File Map
    file_map = FileMap(code) 

    # Diagnostic Engine
    diagnostic = DiagnosticEngine(ruta.name, code, file_map)
    
    # List Token
    tokens = ListTokens()
    
    # Lexer
    lexer = Lexer(code, tokens, diagnostic, file_map)
    tokens = lexer.scan_script()
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
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
    semantic_checker.check_ast(root_node)
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
        return
    
    # Print ast semanticamente correcto
    if cmd == "smt":
        print_ast(root_node)
        return
         
    # Interpreter
    interpreter = Interpreter(root_node, diagnostic)
    interpreter.interpret_main()
    
    if diagnostic.has_errors():
        diagnostic.display()
        diagnostic.clear_engine()
        return
    
   
def cmd_akorn_version():
    print("--Akon Programming Language: v0.1.5--")


def cmd_akorn_help():
    print("--Akon-Cli Commands--\n\n")
    
    print("-ast: Command that executes an akon script and displays its parent node, syntax: akon ast [path to akon script]\n")
    print("-exit: Command that exits the akon repl, syntax: akon repl, can only be done in the repl\n")
    print("-help: displays all akon-cli commands with their function and syntax, syntax: akon help\n")
    print("-repl: activates the interactive mode of the akon programming language, syntax: akon repl\n")
    print("-run: Command that fully executes an akon script, syntax: akon run [path to akon script]\n")
    print("-token: Command that executes an akon script up to the lexer and displays the created tokens, syntax: akon token [path to akon script]\n")
    print("-version: displays the current language version, syntax: akon version\n")
    
        