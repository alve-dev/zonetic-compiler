"""Shared data structures and small utilities for the semantic pass."""

from dataclasses import dataclass, field
from zonc.zonast import ZonType
from zonc.location_file import Span, FileMap
from zonc.utils import levenshtein_zon


@dataclass
class BranchTracker:
    """Tracks how many branches of an if form assign a given variable.
    Used to detect variables that may be uninitialized after an if form.
    Maps name -> [branch_count, decl_span].
    """
    counts: dict = field(default_factory=dict)


@dataclass
class FlowResult:
    """Carries control-flow information upward through statement checking.

    has_global_returned: a `return` was seen at function-body level.
    has_returned:        a `return` was seen anywhere in this block.
    return_type:         the type of the last `return` seen.
    possible_not_return: spans of if forms that may not return on all paths.
    has_given:           a `give` was seen (block-expression value).
    give_type:           the type of the `give` expression.
    give_span:           source span of the `give`.
    has_broken:          a `break` was seen.
    has_continued:       a `continue` was seen.
    """
    has_global_returned: bool = False
    has_returned: bool = False
    return_type: ZonType | None = None
    possible_not_return: list[dict] = field(default_factory=list)
    has_given: bool = False
    give_type: ZonType | None = None
    give_span: Span | None = None
    has_broken: bool = False
    has_continued: bool = False


def leven_hint(name: str, candidates: list[str]) -> str:
    """Return a levenshtein suggestion string, or '' if nothing close."""
    match = levenshtein_zon.suggest(name, candidates)
    return f", did you mean?: `{match}`" if match else ""


def err_span(span: Span, file_map: FileMap) -> Span:
    """One-character span at the end of span, used for closing-brace errors."""
    return Span(span.end - 1, span.end, file_map)