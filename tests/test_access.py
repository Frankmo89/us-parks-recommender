"""Park access (road / boat / flight) in the drive filter and travel labels."""

from __future__ import annotations

import math

import pytest

from src.features import UserProfile
from src.recommender import ParkRecommender, access_label

LA = (34.05, -118.24)
FLIGHT = {"hale", "havo", "npsa", "viis", "gaar", "glba", "katm", "kova", "lacl"}
BOAT = {"chis", "drto", "isro"}


@pytest.fixture(scope="module")
def model() -> ParkRecommender:
    return ParkRecommender()


def _all_ranked(model: ParkRecommender, profile: UserProfile):
    return model.recommend(profile, k=len(model.parks)).set_index("park_code")


def test_la_with_drive_limit_keeps_channel_islands_with_boat_label(model):
    profile = UserProfile(
        biomes=["island", "coast"],
        tags=["kayaking", "wildlife"],
        origin_lat=LA[0],
        origin_lon=LA[1],
        max_drive_hours=8,
    )
    ranked = model.recommend(profile, k=5).set_index("park_code")
    assert "chis" in ranked.index
    hours = float(ranked.loc["chis", "drive_hours"])
    assert 0 < hours <= 8
    assert f"~{hours:.1f}h drive + boat" in ranked.loc["chis", "why"]


def test_road_park_with_drive_limit_has_plain_drive_label(model):
    profile = UserProfile(
        biomes=["desert"], tags=["hiking"], origin_lat=LA[0], origin_lon=LA[1], max_drive_hours=8
    )
    ranked = _all_ranked(model, profile)
    why = ranked.loc["jotr", "why"]
    assert why.endswith("h drive")
    assert "boat" not in why and "flight" not in why


def test_hawaii_volcanoes_excluded_under_60h_drive_limit(model):
    profile = UserProfile(
        biomes=["volcano"], tags=["hiking"], origin_lat=LA[0], origin_lon=LA[1], max_drive_hours=60
    )
    assert "havo" not in set(model.candidates(profile)["park_code"])
    assert "havo" not in set(_all_ranked(model, profile).index)


def test_no_flight_park_passes_any_drive_limit(model):
    profile = UserProfile(
        biomes=[], tags=[], origin_lat=LA[0], origin_lon=LA[1], max_drive_hours=10_000
    )
    codes = set(model.candidates(profile)["park_code"])
    assert codes.isdisjoint(FLIGHT)
    assert BOAT <= codes
    assert len(codes) == len(model.parks) - len(FLIGHT)


def test_no_drive_limit_keeps_hawaii_volcanoes_with_flight_needed(model):
    ranked = _all_ranked(model, UserProfile(biomes=["volcano"], tags=["hiking"]))
    assert "havo" in ranked.index
    assert "flight needed" in ranked.loc["havo", "why"]
    assert math.isnan(float(ranked.loc["havo", "drive_hours"]))
    assert "h drive" not in ranked.loc["havo", "why"]


def test_no_drive_limit_channel_islands_says_boat_needed(model):
    ranked = _all_ranked(model, UserProfile(biomes=["island", "coast"], tags=["kayaking"]))
    assert "boat needed" in ranked.loc["chis", "why"]
    assert "h drive" not in ranked.loc["chis", "why"]


def test_origin_without_max_hours_is_no_drive_limit(model):
    profile = UserProfile(biomes=["volcano"], tags=["hiking"], origin_lat=LA[0], origin_lon=LA[1])
    ranked = _all_ranked(model, profile)
    assert "havo" in ranked.index
    assert "flight needed" in ranked.loc["havo", "why"]


def test_no_drive_limit_labels_cover_every_non_road_park(model):
    ranked = _all_ranked(model, UserProfile(biomes=[], tags=[]))
    for code in FLIGHT:
        assert ranked.loc[code, "why"].endswith("flight needed"), code
    for code in BOAT:
        assert ranked.loc[code, "why"].endswith("boat needed"), code
    road = ranked.loc[ranked["access"] == "road", "why"]
    assert not road.str.contains("needed").any()


def test_access_label_cases():
    assert access_label("road", 2.345) == "~2.3h drive"
    assert access_label("boat", 1.3) == "~1.3h drive + boat"
    assert access_label("boat", float("nan")) == "boat needed"
    assert access_label("flight", None) == "flight needed"
    assert access_label("road", float("nan")) == ""
