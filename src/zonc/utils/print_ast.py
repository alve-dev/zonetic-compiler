"""Debug utility for printing an AST as a formatted table in the terminal.

Call `print_ast(node)` on any AST node to see its full tree structure.
Nodes are expected to optionally implement:
    - get_children() -> list  — child nodes to recurse into
    - get_details()  -> str   — a human-readable summary of the node
    - value                   — fallback if get_details is absent
"""

_HEADER_TYPE   = "NODE TYPE"
_HEADER_DETAIL = "VALUE / DETAIL"


def print_ast(root: object) -> None:
    """Print a tree-structured AST as an aligned two-column table."""
    rows = _collect_rows(root)
    _print_table(rows)


# ------------------------------------------------------------------
# Tree traversal
# ------------------------------------------------------------------

def _collect_rows(root: object) -> list[tuple[str, str]]:
    """Walk the AST depth-first and return (label, detail) pairs."""
    rows = []
    _walk(root, rows, indent="", is_last=True, is_root=True)
    return rows


def _walk(node, rows: list, indent: str, is_last: bool, is_root: bool) -> None:
    marker = "" if is_root else ("└─ " if is_last else "├─ ")
    label  = indent + marker + node.__class__.__name__
    detail = _node_detail(node)

    rows.append((label, detail))

    children = _get_children(node)
    if not children:
        return

    child_indent = indent if is_root else (indent + ("   " if is_last else "│  "))

    for i, child in enumerate(children):
        _walk(child, rows, child_indent, is_last=(i == len(children) - 1), is_root=False)


def _node_detail(node: object) -> str:
    if hasattr(node, "get_details"):
        return str(node.get_details())
    if hasattr(node, "value"):
        return str(node.value)
    return ""


def _get_children(node: object) -> list:
    if not hasattr(node, "get_children"):
        return []
    children = node.get_children()
    if children is None:
        return []
    return [c for c in children if c is not None]


# ------------------------------------------------------------------
# Table rendering
# ------------------------------------------------------------------

def _print_table(rows: list[tuple[str, str]]) -> None:
    col_type   = max(len(_HEADER_TYPE),   max((len(n) for n, _ in rows), default=0))
    col_detail = max(len(_HEADER_DETAIL), max((len(d) for _, d in rows), default=0))

    separator = "-" * (col_type + col_detail + 3)

    print("\n[ ABSTRACT SYNTAX TREE ]")
    print(separator)
    print(_pad(_HEADER_TYPE, col_type) + " | " + _pad(_HEADER_DETAIL, col_detail))
    print(separator)
    for label, detail in rows:
        print(_pad(label, col_type) + " | " + _pad(detail, col_detail))
    print(separator + "\n")


def _pad(text: str, width: int) -> str:
    return str(text).ljust(width)