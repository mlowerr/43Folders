import datetime as dt
from pathlib import Path

import pytest

from folder43 import names
from folder43.generator import apply_plan, build_plan


def test_full_non_leap_year_counts():
    plan = build_plan(Path("out"), dt.date(2026, 1, 1), 1)
    files = [item for item in plan.items if item.kind == "txt"]
    dirs = [item for item in plan.items if item.kind == "dir"]
    assert len(files) == 1 + 12 + 365
    assert len(dirs) == 1 + 2 * (1 + 12 + 365)
    (stats,) = plan.per_year
    assert stats.year == 2026
    assert stats.date_dirs == 1 + 12 + 365
    assert stats.archive_dirs == 1 + 12 + 365
    assert stats.txt_files == 1 + 12 + 365


def test_leap_year_includes_feb_29():
    plan = build_plan(Path("out"), dt.date(2023, 1, 1), 2)
    paths = {item.path for item in plan.items}
    assert Path("out/2023/02/28") in paths
    assert Path("out/2023/02/29") not in paths
    assert Path("out/2024/02/29") in paths
    assert [stats.year for stats in plan.per_year] == [2023, 2024]


def test_mid_year_start_partial_year_counts_as_one():
    plan = build_plan(Path("out"), dt.date(2026, 9, 1), 2)
    paths = {item.path for item in plan.items}
    assert Path("out/2026/08") not in paths
    assert Path("out/2026/09/01") in paths
    assert Path("out/2027/12/31") in paths
    assert Path("out/2028") not in paths
    assert [stats.year for stats in plan.per_year] == [2026, 2027]
    (first,) = [stats for stats in plan.per_year if stats.year == 2026]
    assert first.date_dirs == 1 + 4 + 122  # 2026-09-01..2026-12-31
    assert first.txt_files == 1 + 4 + 122


def test_labels_match_their_folder_paths():
    plan = build_plan(Path("out"), dt.date(2027, 1, 1), 1)
    by_path = {item.path: item for item in plan.items}
    assert by_path[Path("out/2027")].label == "2027"
    assert by_path[Path("out/2027") / names.ARCHIVE_NAME].label == names.ARCHIVE_NAME
    assert by_path[Path("out/2027/01")].label == "2027-01"
    assert by_path[Path("out/2027/01/01")].label == "2027-01-01"
    assert by_path[Path("out/2027/2027.txt")].label == "2027"
    assert by_path[Path("out/2027/01/2027-01.txt")].label == "2027-01"
    assert by_path[Path("out/2027/01/01/2027-01-01.txt")].label == "2027-01-01"


def test_build_plan_rejects_zero_years():
    with pytest.raises(ValueError):
        build_plan(Path("out"), dt.date(2026, 1, 1), 0)


def test_apply_creates_complete_tree(tmp_path):
    root = tmp_path / "43Folders"
    result = apply_plan(build_plan(root, dt.date(2026, 1, 1), 1), quiet=True)
    assert result.created_dirs == 1 + 2 * (1 + 12 + 365)
    assert result.created_files == 1 + 12 + 365
    assert result.skipped_files == 0
    assert (root / "2026/2026.txt").read_text(encoding="utf-8") == "2026\n"
    assert (root / "2026/01/2026-01.txt").read_text(encoding="utf-8") == "2026-01\n"
    assert (root / "2026/01/01/2026-01-01.txt").read_text(encoding="utf-8") == "2026-01-01\n"
    for archive in (
        root / "2026/00-Archive",
        root / "2026/01/00-Archive",
        root / "2026/01/01/00-Archive",
    ):
        assert archive.is_dir()


def test_second_run_is_idempotent_and_never_overwrites(tmp_path):
    root = tmp_path / "43Folders"
    plan = build_plan(root, dt.date(2026, 1, 1), 1)
    apply_plan(plan, quiet=True)
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))

    result = apply_plan(plan, quiet=True)
    after = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert before == after
    assert result.created_dirs == 0
    assert result.created_files == 0
    assert result.skipped_files == 1 + 12 + 365
    assert (root / "2026/2026.txt").read_text(encoding="utf-8") == "2026\n"


def test_existing_archive_contents_and_txt_are_left_untouched(tmp_path):
    root = tmp_path / "43Folders"
    archive = root / "2026/01/00-Archive"
    archive.mkdir(parents=True)
    (archive / "keep.txt").write_text("precious", encoding="utf-8")
    custom = root / "2026/2026.txt"
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text("user notes", encoding="utf-8")

    result = apply_plan(build_plan(root, dt.date(2026, 1, 1), 1), quiet=True)
    assert result.skipped_files == 1
    assert (archive / "keep.txt").read_text(encoding="utf-8") == "precious"
    assert custom.read_text(encoding="utf-8") == "user notes"
    assert (root / "2026/01/2026-01.txt").read_text(encoding="utf-8") == "2026-01\n"