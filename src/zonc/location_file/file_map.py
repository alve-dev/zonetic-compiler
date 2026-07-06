class FileMap:
    """Maps byte offsets in source code to (line, column) positions.

    Built once at startup by scanning the source for newlines.
    All lookups are O(log n) via binary search over the line-start table.
    """

    def __init__(self, source: str) -> None:
        self.source = source

        # _line_starts[i] is the byte offset where line (i+1) begins.
        # We seed with 0 (line 1 starts at the very beginning) and append
        # one sentinel equal to len(source) so the last line is handled
        # cleanly without special-casing.
        self._line_starts = [0]
        for offset, char in enumerate(source):
            if char == '\n':
                self._line_starts.append(offset + 1)
        self._line_starts.append(len(source))

    def get_location(self, offset: int) -> tuple[int, int]:
        """Return the (line, column) for a byte offset in the source.

        Both line and column are 1-based.
        Uses a floor binary search to find which line the offset falls on.
        """
        lo = 0
        hi = len(self._line_starts) - 1
        line_idx = 0

        while lo <= hi:
            mid = (lo + hi) // 2
            if self._line_starts[mid] <= offset:
                line_idx = mid  # best candidate so far, keep searching right
                lo = mid + 1
            else:
                hi = mid - 1

        line = line_idx + 1
        column = offset - self._line_starts[line_idx] + 1
        return line, column