import pytest

from folder43 import names


@pytest.mark.parametrize(
    "bad",
    [
        "",
        ".",
        "..",
        "a/b",
        "a\\b",
        "a:b",
        "a?b",
        "a*b",
        'a"b',
        "a<b",
        "a>b",
        "a|b",
        "CON",
        "com1",
        "LPT9",
        "aux.txt",
        "dot.",
        "dots..",
        " lead",
        "trail ",
        "ctl\x00char",
    ],
)
def test_validate_parent_name_rejects_unsafe_names(bad):
    with pytest.raises(ValueError):
        names.validate_parent_name(bad)


@pytest.mark.parametrize(
    "good",
    ["43Folders", "Notes", "Notes 2026", "my-archive_2", "Reserv.e", "2027"],
)
def test_validate_parent_name_allows_safe_names(good):
    names.validate_parent_name(good)


def test_labels_and_dirs_zero_padded():
    assert names.year_dir(2027) == "2027"
    assert names.month_dir(1) == "01"
    assert names.month_dir(12) == "12"
    assert names.day_dir(1) == "01"
    assert names.day_dir(31) == "31"
    assert names.year_label(2027) == "2027"
    assert names.month_label(2027, 1) == "2027-01"
    assert names.day_label(2027, 1, 1) == "2027-01-01"
    assert names.day_label(2027, 12, 31) == "2027-12-31"


def test_archive_name_sorts_first():
    assert names.ARCHIVE_NAME < "01"