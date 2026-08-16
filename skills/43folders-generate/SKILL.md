---
name: 43folders-generate
description: Use when creating, expanding, or previewing a 43Folders YEAR/MONTH/DAY folder tree with the 43folders CLI — the initial hierarchy, adding the next year or N more years, dry-run previews, or verifying a tree is complete. Triggered by phrases like "create 43Folders for 2027", "add next year's folders", "extend the tree by 2 years", "43folders --dry-run". Do NOT use for writing notes, reviews, filing, or reading an existing tree — use 43folders-tree instead.
---

# 43folders-generate

## What this is

The `43folders` CLI scaffolds a `YEAR/MONTH/DAY` folder tree. Inside every year,
month, and day folder it creates one `00-Archive` directory and one label text
file whose name is the dash-joined folder path:

```
43Folders/
└── 2027/
    ├── 00-Archive/
    ├── 2027.txt
    └── 01/
        ├── 00-Archive/
        ├── 2027-01.txt
        └── 01/
            ├── 00-Archive/
            └── 2027-01-01.txt
```

Month and day folders are zero-padded (`01`-`12`, `01`-`31`) so alphabetical
sort equals chronological sort.

## How to run it

Prefer the installed console script. Fallbacks, in order:

```powershell
43folders [flags]                          # on PATH
C:\git\43Folders\.venv\Scripts\43folders.exe [flags]   # repo venv
python -m folder43 [flags]                 # from the repo root
```

The layout is identical on macOS/Linux (`43folders`, `.venv/bin/43folders`).
CLI output is ASCII-only. Invalid arguments exit with code 2; success is 0.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--name NAME` | `43Folders` | Parent folder name |
| `--start YYYY-MM-DD` | Jan 1 of current year | First date to create (all past days of that year included) |
| `--years N` | `1` | Number of years; a partial start year counts as one |
| `--root DIR` | current directory | Where the parent folder is created |
| `--dry-run` | off | Print the plan; touch nothing |
| `--quiet` | off | One summary line per year (`2026: 378 dated folders`) instead of per-item lines |

## Range semantics (critical)

Generation runs from `--start` through **Dec 31 of `(start year + years - 1)`**.
A start date other than Jan 1 creates the rest of that year and that partial
year counts as a full year:

- `43folders` -> current year, Jan 1 through Dec 31 (past dates included).
- `43folders --start 2026-09-01 --years 2` -> 2026-09-01 through 2027-12-31.
- Leap years are handled (Feb 29 in 2028, not 2027).

## Safety guarantees

- **Never deletes or overwrites anything** — `00-Archive` folders and label
  text files may hold user content. Re-runs are idempotent: existing dirs are
  reused, existing txt files are skipped untouched.
- So it is always safe to re-run the generator over an existing tree to repair
  missing folders.

## Name validation

`--name` must not contain `<>:"/\|?*`, control characters, leading/trailing
whitespace, trailing dots; must not be `.`/`..` or a Windows device name
(CON/PRN/AUX/NUL/COM1-9/LPT1-9). Generated names (`00-Archive`, `YYYY`,
`YYYY-MM`, `YYYY-MM-DD`) are always valid on every OS.

## Recipes

### 1. Initial tree

1. Choose the parent location and name. Run a preview first:
   `43folders --root <dir> --name <Name> --start <YYYY-MM-DD> --years <N> --dry-run`
2. Sanity-check the year lines: a full year shows `378 dated folders`
   (1 year + 12 months + 365/366 days); the partial first year shows a smaller
   count. Each dated folder implies exactly one `00-Archive` dir and one label
   txt (3 items each).
3. Run again without `--dry-run`. Result line reports created/skipped counts.

### 2. Expand for the next year

Find the greatest existing year folder `Y` under the tree root, then:

```
43folders --root <tree-parent> --name <Name> --start <Y+1>-01-01 --years 1
```

For example, after a tree covering 2026: `--start 2027-01-01 --years 1`.
Overlapping ranges are harmless (idempotent), so `--years 2` for a two-year
catch-up also works.

### 3. Backfill years that were never generated

`43folders --root <tree-parent> --name <Name> --start <first-missing-year>-01-01 --years <N>`

### 4. Verify a tree is complete

Re-run the generator (`--quiet`): a complete tree reports `0` created and the
full count skipped. Or run `--dry-run --quiet` and compare year totals against
expected dated-folder counts.

## Warnings

- If the current directory is the app repo root (`C:\git\43Folders`) and
  `--name 43Folders` is used, you would create a nested `43Folders` folder
  inside the repo. Use an explicit `--root`/`--name` instead.
- Prefer `--dry-run --quiet` before any large run (a full year is ~1100 items).