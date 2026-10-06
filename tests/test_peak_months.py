"""Month-aware crowd: a park counts one crowd level quieter outside its peak months."""

from __future__ import annotations

import pytest

from src.features import UserProfile
from src.origins import ORIGINS
from src.recommender import CROWD_PENALTY, ParkRecommender, effective_crowd_rank

YOSE_TRIP = dict(
    biomes=["alpine", "forest"],
    tags=["hiking", "waterfalls", "photography"],
    difficulty="moderate",
    days_needed="2-3",
    crowd_pref="low",
)
CANYON_TRIP = dict(
    biomes=["canyon", "desert"],
    tags=["hiking", "photography"],
    difficulty="moderate",
    days_needed="2-3",
    crowd_pref="low",
)


@pytest.fixture(scope="module")
def model() -> ParkRecommender:
    return ParkRecommender()


def _ranked(model, **profile):
    return model.recommend(UserProfile(**profile), k=63).set_index("park_code")


def _rank(ranked, code):
    return list(ranked.index).index(code) + 1


@pytest.mark.parametrize(
    "crowd, month, expected",
    [
        ("high", None, 2),
        ("high", 7, 2),  # peak month: unchanged
        ("high", 1, 1),  # off-peak: high -> medium
        ("medium", 1, 0),  # off-peak: medium -> low
        ("low", 1, 0),  # low stays low
    ],
)
def test_effective_crowd_rank(crowd, month, expected):
    assert effective_crowd_rank(crowd, "6,7,8,9,10", month) == expected


def test_no_month_keeps_catalog_crowd_penalty(model):
    ranked = _ranked(model, **YOSE_TRIP)
    assert ranked.loc["yose", "crowd_penalty"] == pytest.approx(2 * CROWD_PENALTY)


def test_yosemite_january_vs_july_crowd_penalty(model):
    # Yosemite: crowd high, peak months 6-10 (NPS visits).
    january = _ranked(model, **YOSE_TRIP, month=1)
    july = _ranked(model, **YOSE_TRIP, month=7)
    assert january.loc["yose", "crowd_penalty"] == pytest.approx(0.12)
    assert july.loc["yose", "crowd_penalty"] == pytest.approx(0.24)
    # Same content; January also pays a month penalty (best months 5-10).
    assert january.loc["yose", "content"] == pytest.approx(july.loc["yose", "content"])


def test_crossover_yosemite_off_peak_rises_for_crowd_averse_climber(model):
    # Climbing trip from LA in April: before 0.6.0 Pinnacles ranked first and
    # Yosemite second; April is outside Yosemite's peak, so it now leads.
    lat, lon = ORIGINS["los_angeles"]
    profile = dict(
        biomes=["alpine", "forest"],
        tags=["climbing", "hiking"],
        difficulty="moderate",
        days_needed="2-3",
        crowd_pref="low",
        month=4,
        origin_lat=lat,
        origin_lon=lon,
        max_drive_hours=8,
    )
    ranked = _ranked(model, **profile)
    assert list(ranked.index[:2]) == ["yose", "pinn"]
    assert ranked.loc["yose", "crowd_penalty"] == pytest.approx(0.12)


@pytest.mark.parametrize("month", [3, 11])
def test_crossover_zion_shoulder_season_beats_peak_season_death_valley(model, month):
    # Zion: crowd high, peak 4-10, best months include 3 and 11. Death Valley:
    # crowd medium, and March/November are its peak months.
    lat, lon = ORIGINS["phoenix"]
    ranked = _ranked(
        model, **CANYON_TRIP, month=month, origin_lat=lat, origin_lon=lon, max_drive_hours=8
    )
    assert _rank(ranked, "zion") == 1
    assert _rank(ranked, "deva") == 2
    assert ranked.loc["zion", "crowd_penalty"] == pytest.approx(0.12)
    assert ranked.loc["deva", "crowd_penalty"] == pytest.approx(0.12)


def test_zion_in_peak_month_keeps_full_crowd_penalty(model):
    ranked = _ranked(model, **CANYON_TRIP, month=5)
    assert ranked.loc["zion", "crowd_penalty"] == pytest.approx(0.24)
