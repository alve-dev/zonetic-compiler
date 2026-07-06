"""Levenshtein distance utilities used for typo suggestions in diagnostics.

When a user misypes a keyword or command, the compiler calls `suggest`
to find the closest valid alternative and show it in the error message.
"""


def _edit_distance(a: str, b: str) -> int:
    """Return the Levenshtein edit distance between two strings.

    Uses the classic single-row DP formulation (O(n) space).
    Returns 10 early if the length difference alone makes a close
    match impossible, avoiding unnecessary work.
    """
    if abs(len(a) - len(b)) > 2:
        return 10

    # ensure a is always the longer string so the outer loop is over a
    if len(a) < len(b):
        a, b = b, a

    if not b:
        return len(a)

    prev = list(range(len(b) + 1))

    for i, char_a in enumerate(a):
        curr = [i + 1]
        for j, char_b in enumerate(b):
            insert  = prev[j + 1] + 1
            delete  = curr[j] + 1
            replace = prev[j] + (char_a != char_b)
            curr.append(min(insert, delete, replace))
        prev = curr

    return prev[-1]


def suggest(user_input: str, candidates: list[str], max_distance: int = 5) -> str | None:
    """Return the closest match to user_input from candidates, or None.

    A match is only returned if its edit distance is strictly less than
    max_distance — so increasing max_distance makes suggestions more
    lenient, and setting it to 1 only catches exact matches.
    """
    best_match = None
    best_dist = max_distance

    for candidate in candidates:
        dist = _edit_distance(user_input, candidate)
        if dist < best_dist:
            best_dist = dist
            best_match = candidate

    return best_match