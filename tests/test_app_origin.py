"""Quiz ZIP box -> origin (app/origin.py)."""

from __future__ import annotations

import pytest

from app.origin import ANYWHERE, FOUND, NOT_FOUND, drive_limit, zip_origin


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_empty_box_is_anywhere(raw):
    origin = zip_origin(raw)
    assert origin.status == ANYWHERE
    assert origin.lat is None and origin.lon is None
    assert origin.message == ""
    assert drive_limit(origin, 8) is None


def test_valid_zip_sets_coordinates_and_drive_limit():
    origin = zip_origin(" 02108 ")
    assert origin.status == FOUND
    assert origin.zip_code == "02108"
    assert origin.lat == pytest.approx(42.355097)
    assert origin.lon == pytest.approx(-71.065737)
    assert drive_limit(origin, 8) == 8.0


def test_zip_plus_four_resolves_to_five_digit_zip():
    origin = zip_origin("02108-1234")
    assert origin.status == FOUND
    assert origin.zip_code == "02108"
    assert (origin.lat, origin.lon) == (zip_origin("02108").lat, zip_origin("02108").lon)


@pytest.mark.parametrize("raw", ["123", "2108", "92101-12", "abcde", "00000"])
def test_bad_zip_says_zip_not_found_and_has_no_drive_limit(raw):
    origin = zip_origin(raw)
    assert origin.status == NOT_FOUND
    assert origin.message == "ZIP not found"
    assert drive_limit(origin, 8) is None
