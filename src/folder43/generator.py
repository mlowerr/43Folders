# Copyright (c) 2026 Matthew E. Lowerr
# SPDX-License-Identifier: MIT
"""Core logic: planning and materializing the dated folder tree."""

from __future__ import annotations

import calendar
import datetime as dt
import os
import stat
from dataclasses import dataclass, field
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
    year yields the number of dated folders. Uses a dict so results are
    independent of item ordering.
    """
    counts: dict[int, int] = {}
    for item in plan.items:
        if item.year is not None and item.kind == TXT:
            counts[item.year] = counts.get(item.year, 0) + 1
    return sorted(counts.items())


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


def _is_path_safe(path: Path) -> bool:
    """Return True if *path* exists and is neither a symlink nor a reparse point."""
    return not _is_redirecting_path(path.lstat())


def apply_plan(plan: BuildPlan) -> ApplyResult:
    """Create every item in *plan*. Never deletes or overwrites anything.

    Directories that already exist are left alone; text files that already
    exist are skipped, so a rerun never clobbers user edits. The result
    separates created from skipped items so callers can report either.
    """
    result = ApplyResult()
    for item in plan.items:
        if item.path.exists():
            if not _is_path_safe(item.path):
                if item.kind == DIR:
                    raise UnsafePathError(
                        item.path, "refusing to use redirecting path as directory"
                    )
                raise UnsafePathError(item.path, "label path is not a regular file")
            if item.kind == DIR:
                continue
            if item.path.is_file():
                result.skipped.append(item)
                continue
            raise UnsafePathError(item.path, "label path is not a regular file")
        if item.kind == DIR:
            item.path.mkdir(parents=True)
        else:
            with item.path.open("x", encoding="utf-8", newline="\n") as label_file:
                label_file.write(f"{item.label}\n")
        result.created.append(item)
    return result
