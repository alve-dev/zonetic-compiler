"""Diagnostic engine — the orchestrator of the Zonetic error system.

All compiler passes call `engine.emit(...)` to record errors and warnings.
Once a pass finishes, `engine.display()` sorts, renders, and prints every
diagnostic, then exits with a non-zero status code.

Duplicate suppression
---------------------
The engine tracks how many times each error code has been emitted.
When the same code fires more than once, the renderer receives a flag
that tells it to print a shorter version of the diagnostic — no lengthy
explanation, just the location and message. This avoids flooding the
terminal when a single root cause triggers the same error dozens of times.
"""

import sys

from .error_registry import ERROR_REGISTRY
from .error_code import ErrorCode
from .severity import Severity
from zonc.location_file import Span
from .diagnostic import Diagnostic
from .renderer import DiagnosticRenderer

_MAX_DIAGNOSTICS_SHOWN = 10


class DiagnosticEngine:
    def __init__(self, filename: str, source: str, file_map) -> None:
        self.filename = filename
        self.error_count = 0
        self.warning_count = 0

        self._diagnostics: list[Diagnostic] = []
        self._renderer = DiagnosticRenderer(source, file_map)

        # Counts how many times each error code has been emitted this session.
        # Initialized from ERROR_REGISTRY so new error codes are picked up
        # automatically without needing to update this file.
        self._occurrence: dict[ErrorCode, int] = {code: 0 for code in ERROR_REGISTRY}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(
        self,
        code: ErrorCode,
        args: dict[str, str] | None,
        span_code: list[Span] | None,
        span_labels: list[tuple[Span, str]] | None,
        traceback: bool = False,
        call_stack: list | None = None,
    ) -> None:
        """Record a diagnostic. Call this from any compiler pass.

        Args:
            code:        The error or warning code.
            args:        Template arguments for the error message (may be None).
            span_code:   Source spans highlighted as the primary error site.
            span_labels: (span, label) pairs shown as inline annotations.
            traceback:   If True, attaches a call-stack trace to the diagnostic.
            call_stack:  The call stack to attach when traceback=True.
        """
        if code not in ERROR_REGISTRY:
            print(f"[internal] error code {code!r} is not registered in the Zonetic Error Registry")
            return

        definition = ERROR_REGISTRY[code]

        diagnostic = Diagnostic(
            definition,
            args,
            span_code  if not traceback else None,
            span_labels,
            traceback,
            call_stack if traceback else None,
            self.filename,
        )
        self._diagnostics.append(diagnostic)

        if definition.severity == Severity.ERROR:
            self.error_count += 1
        elif definition.severity == Severity.WARNING:
            self.warning_count += 1

    def has_errors(self) -> bool:
        return self.error_count > 0

    def reset(self) -> None:
        """Clear all recorded diagnostics and reset all counters.
        Used between compilation units in multi-file builds.
        """
        self._diagnostics.clear()
        self.error_count = 0
        self.warning_count = 0
        for code in self._occurrence:
            self._occurrence[code] = 0

    def display(self) -> None:
        """Render and print all diagnostics, then exit with status 1.

        Diagnostics are sorted by their first span's byte offset so they
        appear in source order. After 10 diagnostics the output is truncated
        with a summary — fixing earlier errors often eliminates later ones.
        """
        self._diagnostics.sort(key=lambda d: d.span_errors[0][0].start)

        shown_error = 0
        shown_warning = 0
        for diag in self._diagnostics:
            code = diag.error_definition.error_code
            self._occurrence[code] += 1

            # first occurrence gets the full explanation; repeats get the short form
            is_repeat = self._occurrence[code] > 1
            print(self._renderer.render(diag, is_repeat))
            print()
            print()

            if diag.error_definition.severity == Severity.ERROR: shown_error += 1
            else: shown_warning += 1

            if (shown_error + shown_warning) == _MAX_DIAGNOSTICS_SHOWN:
                self._print_truncation_notice(shown_error, shown_warning)
                break

        sys.exit(1)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _print_truncation_notice(self, shown_error: int, shown_warning: int) -> None:
        remaining_errors   = self.error_count   - shown_error
        remaining_warnings = self.warning_count - shown_warning
        print(
            f"... and {remaining_errors} more error(s), "
            f"plus {remaining_warnings} more warning(s). "
            f"Resolve errors from the top down — "
            f"fixing one often eliminates several others."
        )