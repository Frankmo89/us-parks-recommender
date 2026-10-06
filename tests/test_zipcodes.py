"""ZIP code lookup (src/zipcodes.py)."""

from __future__ import annotations

import pytest

from src.zipcodes import ZIP_NOT_FOUND, ZipNotFoundError, load_zip_table, lookup_zip, normalize_zip


def test_boston_zip_with_leading_zero():
    lat, lon = lookup_zip("02108")
    assert lat == pytest.approx(42.355097)
    assert lon == pytest.approx(-71.065737)


def test_surrounding_spaces_are_trimmed():
    assert lookup_zip(" 02108 ") == lookup_zip("02108")


def test_los_angeles_zip_is_near_the_city_preset():
    from src.origins import ORIGINS

    lat, lon = lookup_zip("90012")
    preset = ORIGINS["los_angeles"]
    assert abs(lat - preset[0]) < 0.1 and abs(lon - preset[1]) < 0.1


@pytest.mark.parametrize("raw", ["00000", "99999", "00001"])
def test_five_digit_zip_not_in_table_raises(raw):
    with pytest.raises(ZipNotFoundError, match=ZIP_NOT_FOUND):
        lookup_zip(raw)


@pytest.mark.parametrize("raw", ["", "2108", "021080", "02108-1234", "abcde", "0210a", None, 2108])
def test_malformed_zip_raises(raw):
    with pytest.raises(ZipNotFoundError, match=ZIP_NOT_FOUND):
        lookup_zip(raw)


def test_error_is_a_value_error_and_keeps_input():
    with pytest.raises(ValueError) as info:
        lookup_zip("123")
    assert info.value.raw == "123"


def test_normalize_zip():
    assert normalize_zip(" 02108") == "02108"
    assert normalize_zip("2108") is None
    assert normalize_zip(None) is None


def test_table_keys_are_five_char_strings():
    table = load_zip_table()
    assert len(table) == 33_791
    assert all(isinstance(code, str) and len(code) == 5 for code in table)
