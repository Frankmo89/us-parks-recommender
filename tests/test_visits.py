"""src/visits.py: raw NPS visit files, the shutdown rule and peak months."""

from __future__ import annotations

import pandas as pd
import pytest

from src import visits
from src.recommender import DATA_PATH

CODES = list(pd.read_csv(DATA_PATH)["park_code"])
FLAT = {m: 100.0 for m in visits.MONTHS}
SUMMER = {m: (300.0 if m in (6, 7, 8) else 50.0) for m in visits.MONTHS}


@pytest.mark.parametrize("year", visits.VISIT_YEARS)
def test_raw_file_covers_every_catalog_park_for_12_months(year):
    data = visits.load_year(year, CODES)
    assert sorted(data) == sorted(CODES)
    assert all(sorted(months) == list(visits.MONTHS) for months in data.values())


def test_seki_maps_to_sequoia_unit_and_kica_stays_separate():
    assert visits.unit_code("seki") == "SEQU"
    assert visits.park_code("SEQU") == "seki"
    assert visits.unit_code("kica") == "KICA"


def test_shutdown_months_average_2023_and_2024_only():
    years = {y: visits.load_year(y, CODES) for y in visits.VISIT_YEARS}
    monthly = visits.load_monthly(CODES)
    for code in CODES:
        for month in (10, 11):
            expected = (years[2023][code][month] + years[2024][code][month]) / 2
            assert monthly[code][month] == pytest.approx(expected)
        expected_jan = sum(years[y][code][1] for y in visits.VISIT_YEARS) / 3
        assert monthly[code][1] == pytest.approx(expected_jan)


def test_peak_is_70_percent_of_busiest_month():
    assert visits.PEAK_CUTOFF == 0.7
    assert visits.peak_months(SUMMER) == [6, 7, 8]
    assert visits.peak_months(FLAT) == list(visits.MONTHS)
    edge = {m: 10.0 for m in visits.MONTHS} | {1: 100.0, 2: 70.0, 3: 69.9}
    assert visits.peak_months(edge) == [1, 2]
    assert visits.peak_months({m: 0.0 for m in visits.MONTHS}) == []


def test_annual_visits_is_sum_of_averaged_months():
    monthly = visits.load_monthly(CODES)
    annual = visits.annual_visits(monthly)
    assert annual["yose"] == pytest.approx(sum(monthly["yose"].values()))
    assert annual["yose"] > annual["kica"] > annual["kova"]


def test_known_peak_months():
    monthly = visits.load_monthly(CODES)
    assert visits.peak_months(monthly["yose"]) == [6, 7, 8, 9, 10]
    assert visits.peak_months(monthly["zion"]) == [4, 5, 6, 7, 8, 9, 10]
    assert visits.peak_months(monthly["dena"]) == [6, 7, 8]


def test_popularity_baseline_ranks_by_average_annual_nps_visits():
    from src.evaluate import popularity_rank
    from src.features import UserProfile
    from src.recommender import ParkRecommender

    model = ParkRecommender()
    annual = visits.annual_visits(visits.load_monthly(CODES))
    expected = sorted(CODES, key=lambda code: (-annual[code], code))[:5]
    assert popularity_rank(model, UserProfile(biomes=[], tags=[]), k=5) == expected
    assert expected[0] == "grsm"
    # Hard filters still apply first.
    utah = popularity_rank(model, UserProfile(biomes=[], tags=[], states=["UT"]), k=5)
    assert utah == sorted(utah, key=lambda code: -annual[code])
    assert set(utah) == {"arch", "brca", "cany", "care", "zion"}
