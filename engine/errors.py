"""Content errors, phrased for the person who wrote the YAML."""

from __future__ import annotations

from pathlib import Path


class ContentError(Exception):
    """A content file is missing, malformed, or internally inconsistent.

    Carries the file and field so the launcher can show an adventure
    author where to look instead of a Python traceback.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | str | None = None,
        field: str | None = None,
    ) -> None:
        self.message = message
        self.path = Path(path) if path is not None else None
        self.field = field
        super().__init__(self.describe())

    def describe(self, *, relative_to: Path | None = None) -> str:
        where = ""
        if self.path is not None:
            shown = self.path
            if relative_to is not None:
                try:
                    shown = self.path.relative_to(relative_to)
                except ValueError:
                    pass
            where = str(shown)
            if self.field:
                where += f" ({self.field})"
            return f"{where}: {self.message}"
        if self.field:
            return f"{self.field}: {self.message}"
        return self.message


def warning(message: str, *, path: Path | str | None = None, field: str | None = None) -> str:
    """Format a non-fatal content problem the same way as an error.

    Warnings are collected on the loaded object rather than raised —
    a typo'd key should tell the author about it, not stop play.
    """
    parts = []
    if path is not None:
        parts.append(str(path))
    if field:
        parts.append(f"({field})")
    prefix = " ".join(parts)
    return f"{prefix}: {message}" if prefix else message
