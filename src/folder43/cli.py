"""Command-line interface for the 43folders generator."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from . import __version__, names
from .generator import apply_plan, build_plan


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
    return count


def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).astimezone().date()


def _print_year_summaries(plan):
    for stats in plan.per_year:
        print(
            f"  {stats.year}: {stats.date_dirs} dated dirs, "
            f"{stats.archive_dirs} archive dirs, {stats.txt_files} txt files"
        )


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
        help="number of years to create (default: 1); a partial start year counts as one",
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
    plan = build_plan(root, start, args.years)

    if args.dry_run:
        if not args.quiet:
            for item in plan.items:
                print(f"  [plan] {'dir' if item.kind == 'dir' else 'txt'}  {item.path}")
        _print_year_summaries(plan)
        print(f"Dry run: {plan.item_count} items planned under {root} - nothing written.")
        return 0

    result = apply_plan(plan, quiet=args.quiet)
    if args.quiet:
        _print_year_summaries(plan)
    print(
        f"Done: created {result.created_dirs} dirs and {result.created_files} txt files, "
        f"skipped {result.skipped_files} existing txt files, under {root}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())