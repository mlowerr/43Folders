# 43folders

Cross-platform (Windows / macOS / Linux) command-line tool that scaffolds a
dated folder tree, ready for the 43 Folders / productivity-folder method.

## Why: your calendar, as a trusted system

`43folders` descends from two landmarks of personal productivity: David Allen's *Getting Things Done* (2001) and Merlin Mann's 43folders.com (2004).

GTD rests on a single premise: *your mind is for having ideas, not holding them.* Anything you might need later belongs in a trusted, reviewable system — and for date-based material, Allen prescribes the classic tickler file: 43 folders (12 months + 31 days) that resurface a note on exactly the day you need it. Merlin Mann's site took its name from that same tickler, and spent a decade exploring a related idea: managing your attention deliberately, rather than ceding it to the unresolved stuff piling up in your life.

This tool scaffolds a modern, digital version of that tickler: a folder for every day of your year — past days included, so you can backfill — nested under month and year folders, each with a `00-Archive` place for what you've already handled, and each labeled with a text file naming the day you're in. The tree becomes the system you trust: notes always have somewhere to land, old material always has somewhere to go, and nothing lives only in your head.

## What it creates

For each year in the range, starting from `--start` (default: January 1 of the
current year) through December 31 of the last year:

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

- `YEAR/MONTH/DAY` folders are zero-padded (`01`–`12`, `01`–`31`) so
  alphabetical sort equals chronological sort.
- A `00-Archive` folder is created inside every year, month and day folder.
- A text file matching the folder label (`2027.txt`, `2027-01.txt`,
  `2027-01-01.txt`) is created in every year, month and day folder, containing
  the label as its first line.
- Every date in the current year is created, including days that have already
  passed.

## Install

```sh
python -m pip install -e .          # from this repository
python -m pip install -e ".[dev]"   # with pytest + ruff for development
```

## Usage

```sh
43folders                                     # parent 43Folders in CWD, full current year
43folders --name Notes                        # different parent folder name
43folders --start 2026-09-01 --years 2        # 2026-09-01 .. 2027-12-31
43folders --root D:\archive                   # create the tree elsewhere
43folders --dry-run                           # print the plan, write nothing
43folders --quiet                             # one summary line per year
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--name NAME` | `43Folders` | Parent folder name |
| `--start YYYY-MM-DD` | Jan 1 of current year | First date to create |
| `--years N` | `1` | Number of years (1-100); a partial start year counts as one |
| `--root DIR` | current directory | Where the parent folder is created |
| `--dry-run` | off | Print the plan without touching the filesystem |
| `--quiet` | off | Print one summary line per year instead of every item |

### Range semantics

Generation runs from `--start` through December 31 of `(start year + years − 1)`.
A start date other than January 1 creates the rest of that year and counts it
as a complete year. Example: `--start 2026-09-01 --years 2` creates
`2026-09-01` through `2027-12-31`.

Ranges may contain at most 100 years and may not extend beyond year 9999.
Use `--quiet` for multi-year runs to avoid printing every planned item.

## Behavior guarantees

- **Never deletes anything.** Archive folders can hold your files; existing
  content is never touched.
- **Idempotent.** Re-running is safe: existing directories are reused and
  existing regular text files are skipped without modification. Label files
  are created atomically so a concurrent writer cannot be overwritten.
- **Does not follow redirecting objects.** A symlink, Windows reparse point
  (including a junction), or other unexpected object at a planned directory or
  label path stops the run instead of redirecting writes.
- **Cross-platform names.** The parent name is validated against characters
  and reserved names that are unsafe on Windows, so a tree created anywhere
  can be copied anywhere. Its UTF-8 byte length and UTF-16 code-unit length
  must both fit the portable 255-unit component limit.

The directory containing the generated parent folder should itself be trusted;
do not run against a parent directory that an untrusted process can replace
while generation is in progress.

Note: bare invocation from this repository's root would create
`C:\git\43Folders\43Folders`. Run from another directory, or pass
`--name`/`--root`.

## Development

```sh
python -m pytest
ruff check .
```

## License

MIT
