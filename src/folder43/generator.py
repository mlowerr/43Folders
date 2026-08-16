"""Core logic: planning and materializing the dated folder tree."""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path

from . import names

DIR = "dir"
TXT = "txt"


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


def _add_level(plan: BuildPlan, year: int, path: Path, label: str) -> None:
    plan.items.append(PlanItem(path, DIR, year=year))
    plan.items.append(PlanItem(path / names.ARCHIVE_NAME, DIR, year=year))
    plan.items.append(PlanItem(path / f"{label}.txt", TXT, label, year))


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
            if item.path.is_dir():
                continue
            item.path.mkdir(parents=True)
            result.created.append(item)
        elif item.path.exists():
            result.skipped.append(item)
        else:
            item.path.write_text(f"{item.label}\n", encoding="utf-8", newline="\n")
            result.created.append(item)
    return result