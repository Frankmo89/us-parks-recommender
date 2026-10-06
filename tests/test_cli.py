"""CLI starting point: --origin presets and --zip."""

from __future__ import annotations

import re

import pytest

from src.cli import main

BASE = ["--biome", "desert", "--tag", "hiking", "--days", "2-3", "--no-remote", "-k", "5"]


def _codes(out: str) -> list[str]:
    return re.findall(r"^\d+\. .* \((\w{4})\)", out, flags=re.M)


def test_zip_sets_origin_and_drive_filter(capsys):
    # 92101 is downtown San Diego.
    main(BASE + ["--zip", "92101", "--max-hours", "4"])
    out = capsys.readouterr().out
    codes = _codes(out)
    assert "jotr" in codes
    assert all(re.search(rf"\({code}\)  score=[\d.]+  [\d.]+h$", out, flags=re.M) for code in codes)


def test_zip_matches_nearby_city_preset(capsys):
    main(BASE + ["--zip", "92101", "--max-hours", "6"])
    by_zip = _codes(capsys.readouterr().out)
    main(BASE + ["--origin", "san_diego", "--max-hours", "6"])
    by_city = _codes(capsys.readouterr().out)
    assert by_zip == by_city


def test_zip_with_leading_zero(capsys):
    main(["--biome", "coast", "--tag", "hiking", "--zip", "02108", "--max-hours", "6"])
    assert "acad" in _codes(capsys.readouterr().out)


@pytest.mark.parametrize("bad", ["00000", "2108", "02108-1234", "abcde"])
def test_bad_zip_exits_with_zip_not_found(capsys, bad):
    with pytest.raises(SystemExit) as info:
        main(BASE + ["--zip", bad])
    assert info.value.code == 2
    assert "ZIP not found" in capsys.readouterr().err


def test_zip_and_origin_together_is_an_error(capsys):
    with pytest.raises(SystemExit) as info:
        main(BASE + ["--zip", "92101", "--origin", "san_diego"])
    assert info.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


def test_no_origin_means_no_drive_hours(capsys):
    main(["--biome", "volcano", "--tag", "hiking"])
    out = capsys.readouterr().out
    assert not re.search(r"score=[\d.]+  [\d.]+h$", out, flags=re.M)
    assert "flight needed" in out
