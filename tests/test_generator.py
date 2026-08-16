import datetime as dt
from pathlib import Path

import pytest

from folder43 import names
from folder43.generator import DIR, TXT, PlanItem, apply_plan, build_plan, year_totals


def test_full_non_leap_year_counts():
    plan = build_plan(Path("out"), dt.date(2026, 1, 1), 1)
    files = [item for item in plan.items if item.kind == TXT]
    dirs = [item for item in plan.items if item.kind == DIR]
    assert len(files) == 1 + 12 + 365
    assert len(dirs) == 1 + 2 * (1 + 12 + 365)
    assert year_totals(plan) == [(2026, 1 + 12 + 365)]


@pytest.mark.parametrize(
    "start,years",
    [
        (dt.date(2026, 1, 1), 1),
        (dt.date(2024, 2, 1), 2),
        (dt.date(2026, 9, 15), 2),
    ],
)
def test_each_dated_folder_gets_exactly_one_archive_and_one_label(start, years):
    plan = build_plan(Path("out"), start, years)
    asserts = {"dir": 0, "archive": 0, "txt": 0}
    for item in plan.items:
        if item.kind == TXT:
            asserts["txt"] += 1
        elif item.path.name == names.ARCHIVE_NAME:
            asserts["archive"] += 1
        elif item.year is not None:
            asserts["dir"] += 1
    assert len(set(asserts.values())) == 1


def test_items_are_ordered_parent_before_child():
    plan = build_plan(Path("out"), dt.date(2026, 9, 15), 2)
    seen = {plan.root}
    for item in plan.items[1:]:
        assert item.path.parent in seen, f"{item.path} appears before its parent"
        seen.add(item.path)


def test_plan_item_rejects_unknown_kind():
    with pytest.raises(ValueError):
        PlanItem(Path("out/x"), "FILE")


def test_plan_item_txt_requires_label():
    with pytest.raises(ValueError):
        PlanItem(Path("out/x"), TXT)


def test_leap_year_includes_feb_29():
    plan = build_plan(Path("out"), dt.date(2023, 1, 1), 2)
    paths = {item.path for item in plan.items}
    assert Path("out/2023/02/28") in paths
    assert Path("out/2023/02/29") not in paths
    assert Path("out/2024/02/29") in paths
    assert year_totals(plan) == [(2023, 1 + 12 + 365), (2024, 1 + 12 + 366)]


def test_mid_year_start_partial_year_counts_as_one():
    plan = build_plan(Path("out"), dt.date(2026, 9, 1), 2)
    paths = {item.path for item in plan.items}
    assert Path("out/2026/08") not in paths
    assert Path("out/2026/09/01") in paths
    assert Path("out/2027/12/31") in paths
    assert Path("out/2028") not in paths
    assert [year for year, _ in year_totals(plan)] == [2026, 2027]
    assert year_totals(plan)[0] == (2026, 1 + 4 + 122)  # 2026-09-01..2026-12-31


def test_mid_month_start_begins_on_start_day():
    plan = build_plan(Path("out"), dt.date(2026, 9, 15), 1)
    paths = {item.path for item in plan.items}
    assert Path("out/2026/09/14") not in paths
    assert Path("out/2026/09/15") in paths
    assert Path("out/2026/09/30") in paths  # partial first month still runs to month end
    assert Path("out/2026/10/01") in paths  # subsequent months start on the 1st
    assert year_totals(plan) == [(2026, 1 + 4 + (16 + 31 + 30 + 31))]


def test_labels_match_their_folder_paths():
    plan = build_plan(Path("out"), dt.date(2027, 1, 1), 1)
    by_path = {item.path: item for item in plan.items}
    assert by_path[Path("out/2027")].label is None
    assert by_path[Path("out/2027") / names.ARCHIVE_NAME].label is None
    assert by_path[Path("out/2027/2027.txt")].label == "2027"
    assert by_path[Path("out/2027/01/2027-01.txt")].label == "2027-01"
    assert by_path[Path("out/2027/01/01/2027-01-01.txt")].label == "2027-01-01"


def test_build_plan_rejects_zero_years():
    with pytest.raises(ValueError):
        build_plan(Path("out"), dt.date(2026, 1, 1), 0)


def test_apply_creates_complete_tree(tmp_path):
    root = tmp_path / "43Folders"
    result = apply_plan(build_plan(root, dt.date(2026, 1, 1), 1))
    dirs = sum(1 for item in result.created if item.kind == DIR)
    files = sum(1 for item in result.created if item.kind == TXT)
    assert dirs == 1 + 2 * (1 + 12 + 365)
    assert files == 1 + 12 + 365
    assert result.skipped == []
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
    apply_plan(plan)
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))

    result = apply_plan(plan)
    after = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert before == after
    assert result.created == []
    assert len(result.skipped) == 1 + 12 + 365
    assert (root / "2026/2026.txt").read_text(encoding="utf-8") == "2026\n"


def test_existing_archive_contents_and_txt_are_left_untouched(tmp_path):
    root = tmp_path / "43Folders"
    archive = root / "2026/01/00-Archive"
    archive.mkdir(parents=True)
    (archive / "keep.txt").write_text("precious", encoding="utf-8")
    custom = root / "2026/2026.txt"
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text("user notes", encoding="utf-8")

    result = apply_plan(build_plan(root, dt.date(2026, 1, 1), 1))
    assert len(result.skipped) == 1
    assert (archive / "keep.txt").read_text(encoding="utf-8") == "precious"
    assert custom.read_text(encoding="utf-8") == "user notes"
    assert (root / "2026/01/2026-01.txt").read_text(encoding="utf-8") == "2026-01\n"