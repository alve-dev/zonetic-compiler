"""CLI entry point for Zonetic.

Parses sys.argv and dispatches to the appropriate command function.
Structure: zon <area> [flag] [arguments]
"""

import sys
from .cmd_zonc import cmd_compile, cmd_repl, cmd_forge, cmd_help
from .buffer import read_lines
from zonc.utils import levenshtein_zon, disassemble
from .cmdregistry import COMMANDS

VERSION = "Zonetic v2.0.0"


def _require_arg(args: list, flag: str, usage: str) -> str | None:
    if not args:
        print(f"[zon error]: No argument provided for {flag}.")
        print(f"-- Usage: {usage}")
        return None
    return args[0]


def _leven_hint(value: str, candidates: list[str]) -> str:
    match = levenshtein_zon.suggest(value, candidates)
    return f"Did you mean?: {match}" if match else "Use zon help to see the available commands."


def _unknown_flag(area: str, flag: str, candidates: list[str]) -> None:
    print(f"[zon error]: Unknown flag '{flag}' for area '{area}'.")
    print(f"-- {_leven_hint(flag, candidates)}")
    sys.exit(1)


# ------------------------------------------------------------------
# Area handlers
# ------------------------------------------------------------------

def _handle_compile(args: list) -> None:
    path = _require_arg(args, "c", "zon c <file>.zon")
    if path:
        cmd_compile(path=path)


def _handle_help(args: list) -> None:
    cmd_help(COMMANDS, args[0] if args else None)


def _handle_st(args: list) -> None:
    if not args:
        print("[zon error]: No flag provided for st.")
        print("-- Usage: zon st <flag>")
        sys.exit(1)

    flag = args[0]
    rest = args[1:]

    if flag == "--file":
        # zon st --file <path.zon> [endkey]
        path = _require_arg(rest, "--file", "zon st --file <path/to/script.zon> [endkey]")
        if path is None:
            return
        endkey = rest[1] if len(rest) > 1 else "EOF"
        cmd_forge(path, endkey)

    elif flag == "--zbc":
        # zon st --zbc <path.zbc> [endkey]
        # reads source interactively then compiles directly to the .zbc path
        path = _require_arg(rest, "--zbc", "zon st --zbc <path/to/output.zbc> [endkey]")
        if path is None:
            return
        endkey = rest[1] if len(rest) > 1 else "EOF"

        print(f"[zon info]: writing bytecode to '{path}'. Type '{endkey}' or EOF to compile.")
        lines = read_lines(endkey)
        if lines is None:
            return
        cmd_compile(source="\n".join(lines), output=path)

    else:
        _unknown_flag("st", flag, ["--file", "--zbc"])


def _handle_vw(args: list) -> None:
    if not args:
        print("[zon error]: No flag provided for vw.")
        print("-- Usage: zon vw <flag>")
        sys.exit(1)

    flag = args[0]
    rest = args[1:]

    match flag:
        case "--vers":
            print(VERSION)

        case "--ast":
            path = _require_arg(rest, "--ast", "zon vw --ast <file>.zon")
            if path:
                cmd_compile(path=path, cmd="ast")

        case "--ast-o":
            path = _require_arg(rest, "--ast-o", "zon vw --ast-o <file>.zon")
            if path:
                cmd_compile(path=path, cmd="asto")

        case "--tokens":
            path = _require_arg(rest, "--tokens", "zon vw --tokens <file>.zon")
            if path:
                cmd_compile(path=path, cmd="token")

        case "--zonasm":
            path = _require_arg(rest, "--zonasm", "zon vw --zonasm <file>.zbc")
            if path:
                disassemble(path)

        case _:
            _unknown_flag("vw", flag, ["--vers", "--ast", "--ast-o", "--tokens", "--zonasm"])


def _handle_repl(args: list) -> None:
    output_zbc     = args[0]
    endkey = args[1] if len(args) > 1 else "EOF"
    cmd_repl(endkey, output_zbc=output_zbc)


# ------------------------------------------------------------------
# Main dispatcher
# ------------------------------------------------------------------

_AREAS = {
    "c":    _handle_compile,
    "help": _handle_help,
    "st":   _handle_st,
    "vw":   _handle_vw,
    "repl": _handle_repl,
}


def run_cli() -> None:
    args = sys.argv[1:]

    if not args:
        print("[zon error]: No command or file specified.")
        print("-- Use zon help to learn the commands and start building.")
        sys.exit(1)

    area    = args[0]
    rest    = args[1:]
    handler = _AREAS.get(area)

    if handler is None:
        print("[zon error]: Unknown command.")
        print(f"-- {_leven_hint(area, list(_AREAS))}")
        sys.exit(1)

    handler(rest)