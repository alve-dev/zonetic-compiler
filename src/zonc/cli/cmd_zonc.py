"""Command implementations for the Zonetic CLI.

Each public function corresponds to one CLI command:
    cmd_run      — compile and run a .zon file (or source string)
    cmd_compile  — compile a .zon file to .zbc bytecode
    cmd_repl     — read code interactively and run it
    cmd_forge    — read code interactively and save it to a .zon file
    cmd_help     — print help for a command or list all commands
"""

import pathlib
from zonc.location_file import FileMap
from zonc.zonc_errors import DiagnosticEngine
from zonc.scanner import Lexer, ListTokens
from zonc.syntatic_normalizer import Normalizer
from zonc.parser import Parser
from zonc.semantic import Semantic
from zonc.utils import print_ast, print_tokens
from zonc.bytecodegen import Emitter
from zonc.optimization import ConstantFolding, DeadCodeElimination
from .keywords import KEYWORDS
from .buffer import read_lines
import os

_END_HINT = "ctrl + z and Enter" if os.name == "nt" else "ctrl + d"


# ------------------------------------------------------------------
# Internal: compiler pipeline
# ------------------------------------------------------------------

def _run_pipeline(source: str, filename: str, cmd: str, output_path: str = None) -> bool:
    """Run the full compiler pipeline on source.

    cmd controls which stage to stop at:
        "token"   — lex only, print token stream
        "ast"     — parse only, print raw AST
        "asto"    — parse + optimize, print optimized AST
        "run"     — compile and run via the VM
        "compile" — compile and save to output_path as .zbc

    Returns True on success, False on error or early exit.
    """
    file_map   = FileMap(source)
    diagnostic = DiagnosticEngine(filename, source, file_map)
    tokens     = ListTokens()

    # -- lex --
    lexer  = Lexer(source, tokens, diagnostic, file_map, KEYWORDS)
    tokens = lexer.scan()

    if diagnostic.has_errors():
        diagnostic.display()
        return False

    if tokens._len() < 2:
        print(f"[zon note]: `{filename}` has nothing to parse.")
        return False

    # -- normalize --
    tokens = Normalizer(tokens, diagnostic, file_map).normalize()

    if diagnostic.has_errors():
        diagnostic.display()
        return False

    if cmd == "token":
        print_tokens(tokens._list)
        return False

    # -- parse --
    root = Parser(tokens, diagnostic, file_map).parse_program(filename)

    if diagnostic.has_errors():
        diagnostic.display()
        return False

    if cmd == "ast":
        print_ast(root)
        return False

    # -- semantic --
    Semantic(diagnostic, file_map).analyze(root)

    if diagnostic.has_errors():
        diagnostic.display()
        return False

    # -- optimizations --
    ConstantFolding(diagnostic).visit_Program(root, True)

    if diagnostic.has_errors():
        diagnostic.display()
        return False

    DeadCodeElimination(diagnostic).eliminate_in_program(root)

    if cmd == "asto":
        print_ast(root)
        return False

    # -- emit --
    # save() generates and writes the .zbc file in one shot
    emitter = Emitter()
    emitter.save(root.stmts, output_path)
    return True


def _load_source(path_str: str) -> tuple[str, str] | None:
    """Read a .zon source file. Returns (source, filename) or None on error."""
    path = pathlib.Path(path_str)

    if not path.exists():
        print("[zon error]: The path or file could not be found.")
        print("-- Double-check your spelling and ensure the file exists.")
        return None

    if not path.is_file():
        print(f"[zon error]: '{path.name}' is not a file.")
        print("-- You provided a directory path. Specify the exact .zon file.")
        return None

    if path.suffix != ".zon":
        print(f"[zon error]: '{path.name}' is not a Zonetic file.")
        print("-- Only .zon files are accepted.")
        return None

    return path.read_text(encoding="utf-8"), path.name


# ------------------------------------------------------------------
# Public commands
# ------------------------------------------------------------------
def cmd_compile(path: str = None, source: str = None, output: str = None, cmd: str = "") -> None:
    """Compile a .zon file to a .zbc bytecode file."""
    if source is None:
        result = _load_source(path)
        if result is None:
            return
        source, filename = result
        out_path = output or str(pathlib.Path(path).with_suffix(".zbc"))
    else:
        filename = "repl"
        out_path = output or "out.zbc"

    success_compile = _run_pipeline(source, filename, cmd, output_path=out_path)
    if out_path and success_compile:
        print(f"[zon info]: compiled to {out_path}")


def cmd_repl(endkey: str, output_zbc: str = None) -> None:
    """Read Zonetic code interactively and run (or compile) it."""
    print(f"[zon info]: REPL mode. Type '{endkey}' or {_END_HINT} to end.")

    lines = read_lines(endkey)
    if lines is None:
        return

    source = "\n".join(lines)

    cmd_compile(source=source, output=output_zbc)


def cmd_forge(output_path: str, endkey: str | None) -> None:
    """Read Zonetic code interactively and save it to a .zon file."""
    target = pathlib.Path(output_path)

    if target.suffix != ".zon":
        print("[zon error]: output file must have the .zon extension.")
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[zon error]: could not create directories. {e}")
        return

    
    print(f"[zon info]: writing to '{target.name}'. Type '{endkey}' or {_END_HINT} to save.")

    lines = read_lines(endkey)
    if lines is None:
        return

    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"[zon info]: file saved at {target}")


# ------------------------------------------------------------------
# Help
# ------------------------------------------------------------------

def cmd_help(commands: dict, command_name: str = None) -> None:
    """Print help for a single command, or list all commands."""
    if command_name and command_name in commands:
        cmd = commands[command_name]

        if hasattr(cmd, 'area'):
            print(f"HELP: Area '{cmd.area}'")

        print(f"Usage: {cmd.usage}\n")
        print(f"Description:\n{cmd.summary}\n")

        if getattr(cmd, 'args', None):
            print("Arguments:")
            for arg in cmd.args:
                print(f"    {arg.name:<14} {arg.description}")
            print()

        if getattr(cmd, 'flags', None):
            print("Flags:")
            for flag in cmd.flags:
                print(f"    {flag.name:<18} {flag.description}")
            print()

        if command_name == "help":
            print('[ o_O] <("Yo Dawg, I heard you like help, so I put some help')
            print('         in your help so you can get help while you help!")\n')
        return

    if command_name and command_name not in commands:
        print(f"[zon error]: Command '{command_name}' not found in help.")
        return

    print("Zonetic Programming Language")
    print("Usage: zon <area> [flags] [arguments]\n")

    categories = {
        "exe":   "Execution",
        "manag": "Management",
        "sys":   "System",
    }

    for cat_key, cat_name in categories.items():
        print(f"{cat_name}:")
        for cmd in commands.values():
            if cmd.category == cat_key:
                print(f"  {cmd.area:<10} {cmd.summary}")
        print()

    print("Use 'zon help [area]' to see all available flags and usage examples.") 