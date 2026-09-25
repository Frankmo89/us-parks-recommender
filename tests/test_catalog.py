"""Catalog load-time validation."""

import pandas as pd
import pytest

from src.catalog import validate_parks
from src.recommender import ParkRecommender


def test_real_catalog_passes_validation():
    model = ParkRecommender()
    assert len(model.parks) == 63


def test_unknown_tag_names_park_code():
    frame = ParkRecommender().parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    frame.loc[frame.index[0], "tags"] = "hiking|not_a_real_tag"
    with pytest.raises(ValueError, match=rf"Park {code}: unknown tag 'not_a_real_tag'"):
        validate_parks(frame)


def test_unknown_biome_names_park_code():
    frame = ParkRecommender().parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    frame.loc[frame.index[0], "biome"] = "swamp"
    with pytest.raises(ValueError, match=rf"Park {code}: unknown biome 'swamp'"):
        validate_parks(frame)


def test_bad_month_token_names_park_code():
    frame = ParkRecommender().parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    frame.loc[frame.index[0], "best_months"] = "5,13,9"
    with pytest.raises(ValueError, match=rf"Park {code}: bad best_months token '13'"):
        validate_parks(frame)


def test_own_biome_repeated_in_tags_is_rejected():
    frame = ParkRecommender().parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    biome = frame.iloc[0]["biome"]
    frame.loc[frame.index[0], "tags"] = f"hiking|{biome}"
    with pytest.raises(
        ValueError,
        match=rf"Park {code}: tags must not repeat the park biome '{biome}'",
    ):
        validate_parks(frame)
