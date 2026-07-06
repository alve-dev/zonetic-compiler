from .severity import Severity
from zonc.location_file import FileMap, Span
from .diagnostic import Diagnostic


class DiagnosticRenderer:
    """Renders a Diagnostic into a human-readable string.

    Output format mirrors rustc-style diagnostics:
        error[E0001]: message
        --> filename:line:col
        3 | inmut x = @
          |         ^-- this character is not recognized
          |
          = note: ...
          [ zonny face ]
    """

    def __init__(self, source: str, file_map: FileMap) -> None:
        self._source = source
        self._file_map = file_map

    # ------------------------------------------------------------------
    # Source line helpers
    # ------------------------------------------------------------------

    def _get_lines(self, line_start: int, line_end: int) -> list[str]:
        start = self._file_map._line_starts[line_start - 1]
        end   = self._file_map._line_starts[line_end]
        return self._source[start:end].split('\n')

    # ------------------------------------------------------------------
    # Note formatting
    # ------------------------------------------------------------------

    def _format_note(self, text: str, line_num_width: int) -> str:
        """Strip common leading indent from a multi-line note string."""
        if not text or not text.strip():
            return ""

        lines = text.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        if not lines:
            return ""

        indent = len(lines[0]) - len(lines[0].lstrip())
        result = []

        for i, line in enumerate(lines):
            content = line[indent:] if len(line) >= indent else line.lstrip()
            if i == 0:
                result.append(content.rstrip())
            else:
                result.append((" " * (9 + line_num_width)) + content.lstrip())

        return "\n".join(result)

    # ------------------------------------------------------------------
    # Span rendering
    # ------------------------------------------------------------------

    def _render_spans(
        self,
        span_codes: list[Span],
        out: list[str],
        span_labels: list[tuple[Span, str]],
        args: dict[str, str],
    ) -> int:
        """Render each primary span with its source lines and label.
        Returns the line-number column width used, for alignment below.
        """
        max_line = max(s.line_end for s in span_codes)
        num_width = len(str(max_line))
        gap = ' ' * num_width

        for i, span in enumerate(span_codes):
            lines = self._get_lines(span.line_start, span.line_end)

            # the split always produces a trailing empty entry for the next line
            if len(self._file_map._line_starts) != span.line_end + 1:
                lines.pop()

            self._render_source_lines(span, lines, num_width, out)

            # pointer row
            label_span, label_text = span_labels[i]
            padding  = " " * label_span.column_start
            pointers = "^" * (label_span.column_end - label_span.column_start)
            out.append(f"{gap} |{padding}{pointers}")

            if label_text is not None:
                out.append(f"-- {label_text.format_map(args)}")

            # separator between multiple spans
            if i != len(span_codes) - 1:
                out.append(f"\n{gap} |\n{gap} ...|\n{gap} |\n")

        return num_width

    def _render_source_lines(
        self,
        span: Span,
        lines: list[str],
        num_width: int,
        out: list[str],
    ) -> None:
        """Append source lines to out, with truncation for long spans."""

        def line_prefix(offset: int) -> str:
            n = span.line_start + offset
            return f"{n} {' ' * (num_width - len(str(n)))}| "

        gap = ' ' * num_width

        if len(lines) == 1:
            out.append(f"{line_prefix(0)}{lines[0]}\n")

        elif len(lines) <= 6:
            for offset, line in enumerate(lines):
                out.append(f"{line_prefix(offset)}{line}\n")

        else:
            # show first 3 lines, elide the middle, show the last line
            for offset in range(3):
                out.append(f"{line_prefix(offset)}{lines[offset]}\n")
            out.append(f"{gap} |\n{gap} ...|\n{gap} |\n")
            last = span.line_end - span.line_start
            out.append(f"{span.line_end} | {lines[last]}\n")

    # ------------------------------------------------------------------
    # Note and Zonny footer
    # ------------------------------------------------------------------

    def _render_footer(
        self,
        out: list[str],
        num_width: int,
        err_def,
        args: dict[str, str] | None,
    ) -> None:
        gap = ' ' * num_width
        out.append(f"\n{gap} |\n")

        note_text = err_def.note if args is None else err_def.note.format_map(args)
        zonny     = err_def.zonny if args is None else err_def.zonny.format_map(args)

        out.append(f"{gap} = note: {self._format_note(note_text, num_width)}\n\n")
        out.append(zonny)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self, diag: Diagnostic, is_repeat: bool) -> str:
        """Return the full diagnostic string ready to print."""
        err_def = diag.error_definition
        args    = diag.args
        out     = []

        # header
        msg = err_def.message.format_map(args) if args else err_def.message
        severity = "error" if err_def.severity == Severity.ERROR else "warning"
        out.append(f"{severity}[{err_def.error_code.name}]: {msg}\n")

        # location + source
        first_label_span = diag.span_errors[0][0]
        out.append(f"--> {diag.name_file}:{first_label_span.line_start}:{first_label_span.column_start}\n")

        num_width = self._render_spans(diag.span_code, out, diag.span_errors, args or {})

        # note and zonny face only on the first occurrence of this error code
        if not is_repeat:
            self._render_footer(out, num_width, err_def, args)

        return "".join(out)