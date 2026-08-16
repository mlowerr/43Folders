"""Validating and formatting folder and file names."""

from __future__ import annotations

import re

ARCHIVE_NAME = "00-Archive"
DEFAULT_PARENT_NAME = "43Folders"

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')

_RESERVED_BASE_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


def validate_parent_name(name: str) -> None:
    """Raise ValueError if *name* would be an unsafe folder name on any platform."""
    if not name:
        raise ValueError("parent folder name must not be empty")
    if name in {".", ".."}:
        raise ValueError("parent folder name must not be '.' or '..'")
    if name.strip() != name:
        raise ValueError("parent folder name must not start or end with whitespace")
    if _INVALID_CHARS.search(name):
        raise ValueError(
            f"parent folder name {name!r} contains characters that are not allowed on all platforms"
        )
    if name.rstrip(".") != name:
        raise ValueError(f"parent folder name {name!r} must not end with a dot")
    if name.split(".")[0].upper() in _RESERVED_BASE_NAMES:
        raise ValueError(f"parent folder name {name!r} is reserved on Windows")


def year_dir(year: int) -> str:
    """Folder name for a year, e.g. ``2027``."""
    return f"{year:04d}"


def month_dir(month: int) -> str:
    """Folder name for a month, e.g. ``01``."""
    return f"{month:02d}"


def day_dir(day: int) -> str:
    """Folder name for a day, e.g. ``01``."""
    return f"{day:02d}"


def year_label(year: int) -> str:
    """Text file label for a year, e.g. ``2027``."""
    return year_dir(year)


def month_label(year: int, month: int) -> str:
    """Text file label for a month, e.g. ``2027-01``."""
    return f"{year_dir(year)}-{month_dir(month)}"


def day_label(year: int, month: int, day: int) -> str:
    """Text file label for a day, e.g. ``2027-01-01``."""
    return f"{year_dir(year)}-{month_dir(month)}-{day_dir(day)}"