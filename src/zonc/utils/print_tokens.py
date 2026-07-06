"""Debug utility for printing a token stream as a formatted table."""

_HEADER_INDEX  = "INDEX"
_HEADER_TYPE   = "TYPE"
_HEADER_LEXEME = "LEXEME"
_HEADER_LINE   = "LINE"


def print_tokens(tokens) -> None:
    """Print the full token stream as an aligned four-column table."""
    if not tokens:
        print("[ ! ] No tokens to display.")
        return

    rows = _collect_rows(tokens)
    _print_table(rows, index_width=len(str(len(tokens))))


# ------------------------------------------------------------------
# Data collection
# ------------------------------------------------------------------

def _collect_rows(tokens) -> list[tuple[str, str, str, str]]:
    """Return (type, lexeme, line) tuples for each token."""
    rows = []
    for token in tokens:
        kind   = str(token._type)
        lexeme = str(token._value).replace('\n', r'\n')
        line   = str(token._span.line_start)
        rows.append((kind, lexeme, line))
    return rows


# ------------------------------------------------------------------
# Table rendering
# ------------------------------------------------------------------

def _print_table(rows: list[tuple[str, str, str]], index_width: int) -> None:
    col_idx    = max(index_width, len(_HEADER_INDEX))
    col_type   = max(len(_HEADER_TYPE),   max((len(r[0]) for r in rows), default=0))
    col_lexeme = max(len(_HEADER_LEXEME), max((len(r[1]) for r in rows), default=0))
    col_line   = max(len(_HEADER_LINE),   max((len(r[2]) for r in rows), default=0))

    separator = "-" * (col_idx + col_type + col_lexeme + col_line + 9)

    def row_str(idx: str, kind: str, lexeme: str, line: str) -> str:
        return (
            idx.ljust(col_idx)       + " | " +
            kind.ljust(col_type)     + " | " +
            lexeme.ljust(col_lexeme) + " | " +
            line.ljust(col_line)
        )

    print("\n[ TOKEN STREAM ]")
    print(separator)
    print(row_str(_HEADER_INDEX, _HEADER_TYPE, _HEADER_LEXEME, _HEADER_LINE))
    print(separator)

    for i, (kind, lexeme, line) in enumerate(rows, start=1):
        print(row_str(str(i).zfill(col_idx), kind, lexeme, line))

    print(separator + "\n")