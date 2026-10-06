"""Optional `states` profile field: validation and hard filter."""

from __future__ import annotations

import pandas as pd
import pytest

from src.catalog import validate_parks
from src.features import STATE_CODES, InvalidProfileError, UserProfile, normalize_states
from src.recommender import ParkRecommender

UTAH_CANYONS = dict(
    biomes=["canyon", "desert"],
    tags=["hiking", "photography", "stargazing"],
    difficulty="moderate",
    days_needed="4-7",
    month=10,
)


@pytest.fixture(scope="module")
def model() -> ParkRecommender:
    return ParkRecommender()


def test_utah_canyons_with_states_ut_returns_utah_parks(model):
    ranked = model.recommend(UserProfile(**UTAH_CANYONS, states=["UT"]), k=5)
    assert set(ranked["park_code"]) == {"arch", "cany", "brca", "zion", "care"}
    assert (ranked["states"] == "UT").all()


def test_utah_canyons_without_states_is_unchanged_and_mixed(model):
    ranked = model.recommend(UserProfile(**UTAH_CANYONS), k=5)
    assert ranked["park_code"].tolist() == ["deva", "blca", "care", "bibe", "cany"]


def test_states_filter_keeps_scores_of_remaining_parks(model):
    everything = model.recommend(UserProfile(**UTAH_CANYONS), k=63).set_index("park_code")
    utah = model.recommend(UserProfile(**UTAH_CANYONS, states=["UT"]), k=63).set_index("park_code")
    assert len(utah) == 5
    for code, row in utah.iterrows():
        assert row["score"] == everything.loc[code, "score"]


def test_multi_state_list_matches_any_listed_state(model):
    profile = UserProfile(biomes=["alpine", "forest"], tags=["hiking"], states=["WA", "OR"])
    ranked = model.recommend(profile, k=10)
    assert set(ranked["park_code"]) == {"mora", "noca", "olym", "crla"}


def test_states_are_trimmed_uppercased_and_deduplicated():
    assert normalize_states([" ut", "UT", "Wa"]) == ["UT", "WA"]


@pytest.mark.parametrize("empty", [None, []])
def test_null_and_empty_list_mean_no_state_filter(model, empty):
    base = model.recommend(UserProfile(**UTAH_CANYONS), k=5)
    got = model.recommend(UserProfile(**UTAH_CANYONS, states=empty), k=5)
    pd.testing.assert_frame_equal(base.reset_index(drop=True), got.reset_index(drop=True))


def test_valid_code_without_parks_returns_empty(model):
    assert model.recommend(UserProfile(**UTAH_CANYONS, states=["DE"]), k=5).empty


@pytest.mark.parametrize("bad", [["XX"], ["Utah"], ["U"], [7], "UT", {"UT"}])
def test_invalid_states_raise_typed_error(model, bad):
    with pytest.raises(InvalidProfileError) as info:
        model.recommend(UserProfile(**UTAH_CANYONS, states=bad), k=5)
    assert info.value.field == "states"


def test_state_codes_cover_states_dc_and_territories():
    assert len(STATE_CODES) == 56
    assert {"DC", "PR", "VI", "AS", "GU", "MP"} <= set(STATE_CODES)


def test_every_catalog_state_code_is_known(model):
    for raw in model.parks["states"]:
        for code in str(raw).split(","):
            assert code.strip() in STATE_CODES


def test_catalog_rejects_unknown_state_code(model):
    frame = model.parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    frame.loc[frame.index[0], "states"] = "ME,ZZ"
    with pytest.raises(ValueError, match=rf"Park {code}: unknown state code 'ZZ'"):
        validate_parks(frame)


def test_comma_separated_catalog_states_match_any_code(model, tmp_path):
    parks = model.parks.copy()
    parks.loc[parks["park_code"] == "yell", "states"] = "WY,MT,ID"
    path = tmp_path / "parks.csv"
    parks.to_csv(path, index=False)
    alt = ParkRecommender(path)
    codes = set(alt.candidates(UserProfile(biomes=[], tags=[], states=["MT"]))["park_code"])
    assert codes == {"glac", "yell"}
