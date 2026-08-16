# Copyright (c) 2026 Matthew E. Lowerr
# SPDX-License-Identifier: MIT
"""Command-line interface for the 43folders generator."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Callable
from pathlib import Path

from . import __version__, names
from .generator import (
    DIR,
    MAX_YEARS,
    BuildPlan,
    PlanItem,
    UnsafePathError,
    apply_plan,
    build_plan,
    year_totals,
)


def _parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid start date {value!r}; expected YYYY-MM-DD")


def _positive_int(value: str) -> int:
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer {value!r}")
    if count < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    if count > MAX_YEARS:
        raise argparse.ArgumentTypeError(f"value must be at most {MAX_YEARS}")
    return count


def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).astimezone().date()


def _kind_word(kind: str) -> str:
    return "dir" if kind == DIR else "txt"


def _display_path(path: Path) -> str:
    """Render a path without allowing control characters to alter terminal output."""
    rendered = []
    for char in str(path):
        codepoint = ord(char)
        if 0x20 <= codepoint <= 0x7E:
            rendered.append(char)
        elif codepoint <= 0xFF:
            rendered.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            rendered.append(f"\\u{codepoint:04x}")
        else:
            rendered.append(f"\\U{codepoint:08x}")
    return "".join(rendered)


def _print_year_summaries(plan: BuildPlan) -> None:
    for year, count in year_totals(plan):
        print(f"  {year}: {count} dated folders")


def _print_item_lines(
    items: list[PlanItem],
    *,
    prefix: str = "",
    suffix: str = "",
    word_fn: Callable[[PlanItem], str] | None = None,
) -> None:
    """Print one line per item with optional prefix and suffix."""
    for item in items:
        word = word_fn(item) if word_fn else _kind_word(item.kind)
        print(f"  {prefix}{word}  {_display_path(item.path)}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="43folders",
        description=(
            "Create a YEAR/MONTH/DAY folder tree with a 00-Archive folder inside every "
            "year, month and day folder, plus a text file in each that records the label."
        ),
    )
    parser.add_argument(
        "--name",
        default=names.DEFAULT_PARENT_NAME,
        metavar="NAME",
        help=f"parent folder name (default: {names.DEFAULT_PARENT_NAME})",
    )
    parser.add_argument(
        "--start",
        type=_parse_date,
        metavar="YYYY-MM-DD",
        help="first date to create (default: January 1 of the current year)",
    )
    parser.add_argument(
        "--years",
        type=_positive_int,
        default=1,
        metavar="N",
        help=(
            f"number of years to create, 1-{MAX_YEARS} (default: 1); "
            "a partial start year counts as one"
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        metavar="DIR",
        help="directory in which the parent folder is created (default: current directory)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan without creating anything")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print one summary line per year instead of each item",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        names.validate_parent_name(args.name)
    except ValueError as exc:
        parser.error(str(exc))

    root = args.root / args.name
    start = args.start if args.start is not None else _today().replace(month=1, day=1)
    try:
        plan = build_plan(root, start, args.years)
    except ValueError as exc:
        parser.error(str(exc))
    display_root = _display_path(root)

    if args.dry_run:
        if not args.quiet:
            _print_item_lines(plan.items, prefix="[plan] ")
        _print_year_summaries(plan)
        print(f"Dry run: {len(plan.items)} items planned under {display_root} - nothing written.")
        return 0

    try:
        result = apply_plan(plan)
    except UnsafePathError as exc:
        print(f"Error: {exc.reason}: {_display_path(exc.path)}", file=sys.stderr)
        return 1
    if not args.quiet:
        _print_item_lines(result.created)
        _print_item_lines(
            result.skipped,
            word_fn=lambda item: "skip",
            suffix=" (already exists)",
        )
    _print_year_summaries(plan)
    dirs = sum(1 for item in result.created if item.kind == DIR)
    files = len(result.created) - dirs
    print(
        f"Done: created {dirs} dirs and {files} txt files, "
        f"skipped {len(result.skipped)} existing txt files, under {display_root}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
