"""Core logic: planning and materializing the dated folder tree."""

from __future__ import annotations

import calendar
import datetime as dt
import os
import stat
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path

from . import names

DIR = "dir"
TXT = "txt"
MAX_YEARS = 100


@dataclass(frozen=True)
class PlanItem:
    """One unit of work: a directory or a labeled text file."""

    path: Path
    kind: str  # DIR or TXT
    label: str | None = None  # required for TXT; file content
    year: int | None = None  # year the item belongs to; None for the parent folder

    def __post_init__(self) -> None:
        if self.kind not in (DIR, TXT):
            raise ValueError(f"unknown plan item kind: {self.kind!r}")
        if self.kind == TXT and self.label is None:
            raise ValueError("txt plan items require a label")


@dataclass
class BuildPlan:
    """The complete ordered set of directories and files to create."""

    root: Path
    items: list[PlanItem] = field(default_factory=list)


@dataclass
class ApplyResult:
    """Items materialized by applying a plan, separated by outcome."""

    created: list[PlanItem] = field(default_factory=list)
    skipped: list[PlanItem] = field(default_factory=list)


class UnsafePathError(FileExistsError):
    """A planned path is a redirecting or otherwise incompatible filesystem object."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(reason)
        self.path = path
        self.reason = reason


def _add_level(plan: BuildPlan, year: int, path: Path, label: str) -> None:
    plan.items.append(PlanItem(path, DIR, year=year))
    plan.items.append(PlanItem(path / names.ARCHIVE_NAME, DIR, year=year))
    plan.items.append(PlanItem(path / f"{label}.txt", TXT, label, year))


def _is_redirecting_path(path_stat: os.stat_result) -> bool:
    """Return whether an lstat result identifies a symlink or Windows reparse point."""
    file_attributes = getattr(path_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(path_stat.st_mode) or bool(
        file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def year_totals(plan: BuildPlan) -> list[tuple[int, int]]:
    """Ordered ``(year, dated_folder_count)`` pairs for *plan*.

    Every dated folder carries exactly one label file, so counting labels per
    year yields the number of dated folders. Items are appended year by year,
    which makes a ``groupby`` over ``item.year`` safe.
    """
    totals = []
    for year, items in groupby(plan.items, key=lambda item: item.year):
        if year is None:
            continue
        totals.append((year, sum(1 for item in items if item.kind == TXT)))
    return totals


def build_plan(root: Path, start: dt.date, years: int) -> BuildPlan:
    """Plan the full tree for [start, Dec 31 of (start.year + years - 1)].

    A partial start year counts as a full year, so it is covered by *years*.
    Every dated folder gets one archive folder and one label file, whose name
    is the dash-joined path of the folders leading to it.
    """
    if years < 1:
        raise ValueError("years must be at least 1")
    if years > MAX_YEARS:
        raise ValueError(f"years must be at most {MAX_YEARS}")
    if years > dt.date.max.year - start.year + 1:
        raise ValueError(f"date range must not extend beyond year {dt.date.max.year}")

    plan = BuildPlan(root=root)
    plan.items.append(PlanItem(root, DIR))
    last_year = start.year + years - 1

    for year in range(start.year, last_year + 1):
        year_name = names.year_dir(year)
        year_path = root / year_name
        _add_level(plan, year, year_path, year_name)

        for month in range(start.month if year == start.year else 1, 13):
            month_name = names.month_dir(month)
            month_path = year_path / month_name
            _add_level(plan, year, month_path, f"{year_name}-{month_name}")

            first_day = start.day if (year, month) == (start.year, start.month) else 1
            for day in range(first_day, calendar.monthrange(year, month)[1] + 1):
                day_name = names.day_dir(day)
                day_path = month_path / day_name
                _add_level(plan, year, day_path, f"{year_name}-{month_name}-{day_name}")

    return plan


def apply_plan(plan: BuildPlan) -> ApplyResult:
    """Create every item in *plan*. Never deletes or overwrites anything.

    Directories that already exist are left alone; text files that already
    exist are skipped, so a rerun never clobbers user edits. The result
    separates created from skipped items so callers can report either.
    """
    result = ApplyResult()
    for item in plan.items:
        if item.kind == DIR:
            try:
                item.path.mkdir(parents=True)
            except FileExistsError:
                path_stat = item.path.lstat()
                if _is_redirecting_path(path_stat):
                    raise UnsafePathError(
                        item.path, "refusing to use redirecting path as directory"
                    )
                if stat.S_ISDIR(path_stat.st_mode):
                    continue
                raise
            result.created.append(item)
        else:
            try:
                with item.path.open("x", encoding="utf-8", newline="\n") as label_file:
                    label_file.write(f"{item.label}\n")
            except FileExistsError:
                path_stat = item.path.lstat()
                if not _is_redirecting_path(path_stat) and stat.S_ISREG(path_stat.st_mode):
                    result.skipped.append(item)
                    continue
                raise UnsafePathError(item.path, "label path is not a regular file")
            result.created.append(item)
    return result
