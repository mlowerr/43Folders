import datetime as dt
import sys

import pytest

from folder43 import cli, names


def test_default_start_is_jan_1_of_current_year(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_today", lambda: dt.date(2026, 7, 5))
    rc = cli.main(["--root", str(tmp_path), "--quiet"])
    assert rc == 0
    root = tmp_path / "43Folders"
    assert (root / "2026/01/01/2026-01-01.txt").exists()
    assert (root / "2026/12/31/2026-12-31.txt").exists()
    assert not (root / "2025").exists()
    assert not (root / "2027").exists()


def test_custom_name_and_multiple_years(tmp_path):
    rc = cli.main(
        ["--root", str(tmp_path), "--name", "Notes", "--start", "2027-01-01", "--years", "3", "--quiet"]
    )
    assert rc == 0
    base = tmp_path / "Notes"
    assert (base / "2027").is_dir()
    assert (base / "2028").is_dir()
    assert (base / "2029").is_dir()
    assert not (base / "2030").exists()
    assert (base / "2029/12/31/2029-12-31.txt").exists()
    assert not (tmp_path / "43Folders").exists()


def test_start_mid_year_runs_through_end_of_last_year(tmp_path):
    rc = cli.main(["--root", str(tmp_path), "--start", "2026-09-01", "--years", "2", "--quiet"])
    assert rc == 0
    base = tmp_path / "43Folders"
    assert not (base / "2026/08").exists()
    assert (base / "2026/09/01").is_dir()
    assert (base / "2027/12/31").is_dir()


def test_dry_run_creates_nothing(tmp_path, capsys):
    rc = cli.main(["--root", str(tmp_path), "--start", "2026-01-01", "--years", "1", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[plan]" in out
    assert "Dry run" in out
    assert list(tmp_path.rglob("*")) == []


def test_quiet_prints_one_summary_line_per_year(tmp_path, capsys):
    rc = cli.main(["--root", str(tmp_path), "--start", "2026-12-01", "--years", "2", "--quiet"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2026: 33 dated folders" in out  # 1 year + 1 month + 31 days
    assert "2027: 378 dated folders" in out
    assert "[plan]" not in out
    assert "Done:" in out


def test_default_name_is_valid():
    names.validate_parent_name(names.DEFAULT_PARENT_NAME)


@pytest.mark.parametrize(
    "extra",
    [
        ["--start", "2026-13-01"],
        ["--start", "nope"],
        ["--years", "0"],
        ["--years", "x"],
        ["--years", "101"],
        ["--name", "a/b"],
        ["--name", "CON"],
        ["--name", "note."],
        ["--name", " "],
        ["--start"],
    ],
)
def test_invalid_arguments_exit_with_error(tmp_path, extra):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--root", str(tmp_path)] + extra)
    assert exc.value.code == 2


def test_version_flag(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "43folders" in capsys.readouterr().out


def test_range_past_year_9999_is_cli_error(tmp_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--root", str(tmp_path), "--start", "9999-12-31", "--years", "2"])
    assert exc.value.code == 2


def test_years_above_max_rejected_by_cli(tmp_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--root", str(tmp_path), "--start", "2026-01-01", "--years", "101"])
    assert exc.value.code == 2


def test_display_path_supplementary_plane(tmp_path, capsys):
    root = tmp_path / "emoji-\U0001f600"
    rc = cli.main(["--root", str(root), "--start", "2026-12-31", "--dry-run", "--quiet"])
    assert rc == 0
    output = capsys.readouterr().out
    assert "\\U0001f600" in output
    assert output.isascii()


def test_today_leap_year(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_today", lambda: dt.date(2024, 2, 29))
    rc = cli.main(["--root", str(tmp_path), "--quiet"])
    assert rc == 0
    root = tmp_path / "43Folders"
    assert (root / "2024/02/29/2024-02-29.txt").exists()
    assert not (root / "2025").exists()


def test_paths_are_safely_escaped_in_output(tmp_path, capsys):
    unsafe_root = tmp_path / "line\nbreak-☃"
    rc = cli.main(
        ["--root", str(unsafe_root), "--start", "2026-12-31", "--dry-run", "--quiet"]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "line\\x0abreak-\\u2603" in output
    assert "line\nbreak" not in output
    assert output.isascii()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows cannot create directories with control characters in names",
)
@pytest.mark.parametrize("collision", ["redirecting directory", "label directory"])
def test_filesystem_errors_safely_escape_paths(tmp_path, capsys, collision):
    unsafe_parent = tmp_path / "line\nbreak-☃"
    root = unsafe_parent / "Notes"
    if collision == "redirecting directory":
        unsafe_parent.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        root.symlink_to(outside, target_is_directory=True)
        expected_reason = "refusing to use redirecting path as directory"
    else:
        label = root / "2026/2026.txt"
        label.mkdir(parents=True)
        expected_reason = "label path is not a regular file"

    rc = cli.main(
        [
            "--root",
            str(unsafe_parent),
            "--name",
            "Notes",
            "--start",
            "2026-12-31",
            "--quiet",
        ]
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert expected_reason in captured.err
    assert "line\\x0abreak-\\u2603" in captured.err
    assert "line\nbreak" not in captured.err
    assert captured.err.isascii()
