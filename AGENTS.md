# AGENTS.md

Guidance for AI agents and human maintainers working on this repository.

## Project

`43folders` — a cross-platform (Windows/macOS/Linux) Python CLI that scaffolds a
`YEAR/MONTH/DAY` folder tree with a `00-Archive` folder and a labeled text file
inside every year, month, and day folder. Inspired by David Allen's *Getting
Things Done* and Merlin Mann's 43folders.com (see README preamble).

Stack: **Python >= 3.10, stdlib only** (argparse, pathlib, calendar, datetime).
No runtime dependencies by design. Distribution name `43folders`; import
package `folder43`.

## Commands (from repo root)

```powershell
.\.venv\Scripts\python.exe -m pytest -q     # run tests (60+)
.\.venv\Scripts\ruff.exe check .            # lint (line-length 100)
.\.venv\Scripts\43folders.exe --help        # the installed console script
.\.venv\Scripts\python.exe -m folder43 --dry-run --root <dir> --name <name>
```

Setup (first time): `python -m venv .venv`, then
`.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`.

**Always run pytest and ruff after any change; the repo ships with a clean
(0-error) ruff baseline.**

## Architecture

```
src/folder43/
├── __init__.py    # __version__ only
├── __main__.py    # python -m entry point
├── cli.py         # argparse, validation, ALL presentation/printing
├── generator.py   # pure model: plan + apply (no printing)
└── names.py       # name validation + zero-padded folder names
tests/             # pytest; test_names, test_generator, test_cli
```

- **generator.py** — the core:
  - `PlanItem` — frozen dataclass `(path, kind, label=None, year=None)`;
    `__post_init__` enforces invariants (kind ∈ {DIR, TXT}; TXT requires
    label). Never construct invalid items.
  - `build_plan(root, start, years)` — nested year/month/day loops using
    `calendar.monthrange`; one `_add_level` call appends dir + archive + label
    txt per dated folder. Items are appended **in order**: parent before
    child, year before month before day (dry-run output and `year_totals`
    depend on this ordering).
  - `year_totals(plan)` — derived per-year counts (groupby over `item.year`).
    **Derive, never store parallel counters.**
  - `apply_plan(plan)` — does I/O only; returns `ApplyResult(created,
    skipped)`; never deletes, never overwrites; existing dirs skipped
    silently, existing txt files skipped (reported). No printing.
- **cli.py** — owns every `print`. `--dry-run` prints `[plan]` lines + year
  summaries; real runs print created/skipped lines + year summaries + `Done:`
  line. `_today()` is monkeypatchable for tests. Output text is **ASCII-only**
  (Windows consoles mangle non-ASCII, e.g. em-dashes render as `�`).

## Core invariants (do not break)

1. **Never delete or modify existing filesystem content** — `00-Archive`
   folders hold user files; txt files may hold user edits. Re-runs are
   idempotent.
2. **Range semantics**: generation runs from `--start` through Dec 31 of
   `(start.year + years − 1)`. A partial start year counts as a full year
   (e.g. `--start 2026-09-01 --years 2` → 2026-09-01 .. 2027-12-31). Default
   `--start` = Jan 1 of the current year (all dates, past included).
3. **One dated folder → exactly one `00-Archive` dir + one label txt.**
   Label = dash-joined folder path (`2027-01-01`). Month/day names are
   zero-padded (`01`–`12`, `01`–`31`) so lexicographic sort is chronological.
4. **`PlanItem` validity is enforced at construction** — keep it that way;
   don't add runtime guard branches in `apply_plan`.
5. **Single source of truth**: `plan.items` is the model. Counts are derived,
   not maintained alongside.

## Conventions

- stdlib only; dataclasses for small models; type hints everywhere
  (`from __future__ import annotations`); `f-string` labels built from folder
  names (do not re-add `year_label`/`month_label`/`day_label` helpers — the
  label == folder path property is by construction).
- Docstrings on public functions; minimal inline comments.
- Validation lives at boundaries: argparse types in cli, `__post_init__` in
  PlanItem, `validate_parent_name` in names (rejects chars/reserved names
  unsafe on Windows — applies on all platforms so trees are portable).
- Tests: pytest with `tmp_path` fixtures (never touch the repo root — no
  `43Folders` subfolder may appear in the project directory); `monkeypatch`
  `cli._today` for default-start tests; parametrize to cover leap years
  (2024), mid-year and mid-month starts, multi-year runs.
- ruff: default rule set, line-length 100.

## Known behavior notes

- Python 3.11+ `date.fromisoformat` accepts unpadded dates (`2026-9-1`);
  leniency is accepted.
- A file blocking a planned dir path raises `FileExistsError` (unhandled →
  traceback); accepted for v1.
- `BuildPlan.root` mirrors `items[0].path` (semantic handle; construction
  sites are trivial).
