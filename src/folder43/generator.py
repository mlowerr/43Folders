"""Core logic: planning and materializing the dated folder tree."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from . import names


@dataclass(frozen=True)
class PlanItem:
    """One unit of work: a directory or text file to create."""

    path: Path
    kind: str  # "dir" or "txt"
    label: str
    year: int | None


@dataclass
class YearStats:
    """Planned item counts for a single year."""

    year: int
    date_dirs: int = 0
    archive_dirs: int = 0
    txt_files: int = 0


@dataclass
class BuildPlan:
    """The complete ordered set of directories and files to create."""

    root: Path
    items: list[PlanItem] = field(default_factory=list)
    per_year: list[YearStats] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.items)


@dataclass
class ApplyResult:
    """Counts produced by materializing a plan."""

    created_dirs: int = 0
    created_files: int = 0
    skipped_files: int = 0


def build_plan(root: Path, start: dt.date, years: int) -> BuildPlan:
    """Plan the full tree for [start, Dec 31 of (start.year + years - 1)].

    A partial start year counts as a full year, so it is covered by *years*.
    """
    if years < 1:
        raise ValueError("years must be at least 1")

    end = dt.date(start.year + years - 1, 12, 31)
    plan = BuildPlan(root=root)
    plan.items.append(PlanItem(root, "dir", root.name, None))

    per_year: dict[int, YearStats] = {}
    added_months: set[tuple[int, int]] = set()

    current = start
    while current <= end:
        stats = per_year.get(current.year)
        if stats is None:
            stats = YearStats(current.year)
            per_year[current.year] = stats
            year_path = root / names.year_dir(current.year)
            plan.items.append(PlanItem(year_path, "dir", names.year_label(current.year), current.year))
            plan.items.append(
                PlanItem(year_path / names.ARCHIVE_NAME, "dir", names.ARCHIVE_NAME, current.year)
            )
            plan.items.append(
                PlanItem(
                    year_path / f"{names.year_label(current.year)}.txt",
                    "txt",
                    names.year_label(current.year),
                    current.year,
                )
            )
            stats.date_dirs += 1
            stats.archive_dirs += 1
            stats.txt_files += 1

        month_key = (current.year, current.month)
        if month_key not in added_months:
            added_months.add(month_key)
            month_path = year_path / names.month_dir(current.month)
            label = names.month_label(current.year, current.month)
            plan.items.append(PlanItem(month_path, "dir", label, current.year))
            plan.items.append(
                PlanItem(month_path / names.ARCHIVE_NAME, "dir", names.ARCHIVE_NAME, current.year)
            )
            plan.items.append(PlanItem(month_path / f"{label}.txt", "txt", label, current.year))
            stats.date_dirs += 1
            stats.archive_dirs += 1
            stats.txt_files += 1

        day_path = month_path / names.day_dir(current.day)
        label = names.day_label(current.year, current.month, current.day)
        plan.items.append(PlanItem(day_path, "dir", label, current.year))
        plan.items.append(PlanItem(day_path / names.ARCHIVE_NAME, "dir", names.ARCHIVE_NAME, current.year))
        plan.items.append(PlanItem(day_path / f"{label}.txt", "txt", label, current.year))
        stats.date_dirs += 1
        stats.archive_dirs += 1
        stats.txt_files += 1

        current += dt.timedelta(days=1)

    plan.per_year = [per_year[year] for year in sorted(per_year)]
    return plan


def apply_plan(plan: BuildPlan, *, quiet: bool = False) -> ApplyResult:
    """Create every item in *plan*. Never deletes or overwrites anything.

    Directories are created with ``exist_ok=True``; text files that already
    exist are skipped (and their contents left untouched).
    """
    result = ApplyResult()
    for item in plan.items:
        if item.kind == "dir":
            existed = item.path.exists()
            item.path.mkdir(parents=True, exist_ok=True)
            if not existed:
                result.created_dirs += 1
            elif not quiet:
                print(f"  dir   {item.path} (already exists)")
        else:
            if item.path.exists():
                result.skipped_files += 1
                if not quiet:
                    print(f"  skip  {item.path} (already exists)")
                continue
            item.path.write_text(f"{item.label}\n", encoding="utf-8", newline="\n")
            result.created_files += 1
            if not quiet:
                print(f"  txt   {item.path}")
    return result