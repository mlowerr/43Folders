"""Validating and formatting folder names."""

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
        "CONIN$",
        "CONOUT$",
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
    utf8_bytes = len(name.encode("utf-8"))
    utf16_units = len(name.encode("utf-16-le")) // 2
    if utf8_bytes > 255 or utf16_units > 255:
        raise ValueError("parent folder name exceeds the portable 255-unit component limit")


def year_dir(year: int) -> str:
    """Folder name (and label) for a year, e.g. ``2027``."""
    return f"{year:04d}"


def month_dir(month: int) -> str:
    """Folder name for a month, e.g. ``01``."""
    return f"{month:02d}"


def day_dir(day: int) -> str:
    """Folder name for a day, e.g. ``01``."""
    return f"{day:02d}"
