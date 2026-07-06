"""Interactive line buffer — shared by the REPL and the file forge.

`read_lines(endkey)` reads lines from stdin until the user types `endkey`
(case-insensitive) or sends EOF (Ctrl+D / Ctrl+Z+Enter).

On Linux/macOS it sets up readline with:
  - persistent history in ~/.zonhistoryrepl
  - tab-completion for Zonetic keywords and EOF

On Windows (or when readline is unavailable) it falls back to a plain
input() loop that behaves identically except without history or completion.
"""

import os
import sys
from .keywords import KEYWORDS

_HISTORY_FILE = os.path.expanduser("~/.zonhistoryrepl")
_HISTORY_LENGTH = 500
_COMPLETE_WORDS = ["EOF"] + list(KEYWORDS)


def _setup_readline() -> bool:
    """Try to initialise readline with history and tab-completion.
    Returns True on success, False if readline is unavailable.
    """
    try:
        import readline
        import atexit

        if not os.path.exists(_HISTORY_FILE):
            try:
                open(_HISTORY_FILE, 'a').close()
            except OSError:
                print('[ X_X] <("Warning: cannot write history file. Session won\'t be saved.")')

        try:
            readline.read_history_file(_HISTORY_FILE)
        except FileNotFoundError:
            pass

        readline.set_history_length(_HISTORY_LENGTH)
        atexit.register(readline.write_history_file, _HISTORY_FILE)
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind("tab: complete")

        def _completer(text, state):
            options = [w for w in _COMPLETE_WORDS if w.startswith(text)]
            return options[state] if state < len(options) else None

        readline.set_completer(_completer)
        return True

    except ImportError:
        return False


def read_lines(endkey: str) -> list[str] | None:
    """Read lines interactively until endkey or EOF.

    Returns the collected lines, or None if the user interrupted
    without entering anything.
    """
    has_readline = os.name != "nt" and _setup_readline()

    lines = []
    try:
        import readline as _rl  # only used for add_history below

        while True:
            line = input(">> ").rstrip('\r')
            if line.strip().upper() == endkey.upper():
                break
            lines.append(line)
            if has_readline:
                _rl.add_history(line)

    except EOFError:
        print()

    except KeyboardInterrupt:
        print("\n[zon info]: input interrupted.")
        return None

    if not lines:
        print("[zon note]: No code entered. Operation cancelled.")
        return None

    return lines