"""Catalog load-time validation."""

import pandas as pd
import pytest

from src.catalog import validate_parks
from src.features import TAG_VOCAB, parse_tags
from src.recommender import DATA_PATH, ParkRecommender


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
    frame.loc[frame.index[0], "biomes"] = "swamp"
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
    # Repeat the park's first listed biome inside tags.
    biome = str(frame.iloc[0]["biomes"]).split("|")[0]
    frame.loc[frame.index[0], "tags"] = f"hiking|{biome}"
    with pytest.raises(
        ValueError,
        match=rf"Park {code}: tags must not repeat the park biome '{biome}'",
    ):
        validate_parks(frame)


def test_yellowstone_lists_alpine_and_forest():
    parks = ParkRecommender().parks.set_index("park_code")
    biomes = set(str(parks.loc["yell", "biomes"]).split("|"))
    assert biomes == {"alpine", "forest"}


def test_invalid_access_value_names_park_code():
    frame = ParkRecommender().parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    frame.loc[frame.index[0], "access"] = "ferry"
    with pytest.raises(ValueError, match=rf"Park {code}: access must be one of"):
        validate_parks(frame)


def test_missing_access_value_is_rejected():
    frame = ParkRecommender().parks.head(1).copy()
    code = frame.iloc[0]["park_code"]
    frame.loc[frame.index[0], "access"] = None
    with pytest.raises(ValueError, match=rf"Park {code}: access must be one of"):
        validate_parks(frame)


def test_access_column_is_required():
    frame = ParkRecommender().parks.head(1).drop(columns=["access"])
    with pytest.raises(ValueError, match=r"missing columns: \['access'\]"):
        validate_parks(frame)


def test_access_matches_approved_list():
    parks = ParkRecommender().parks.set_index("park_code")
    flight = {"hale", "havo", "npsa", "viis", "gaar", "glba", "katm", "kova", "lacl"}
    boat = {"chis", "drto", "isro"}
    assert set(parks.index[parks["access"] == "flight"]) == flight
    assert set(parks.index[parks["access"] == "boat"]) == boat
    assert set(parks["access"].unique()) == {"road", "boat", "flight"}


def _one_park(**overrides) -> pd.DataFrame:
    """A minimal valid one-row catalog, independent of data/parks.csv."""
    row = {
        "park_code": "test",
        "states": "UT",
        "biomes": "desert",
        "tags": "hiking|stargazing",
        "best_months": "3,4,10",
        "peak_months": "4,5,6",
        "access": "road",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_minimal_catalog_row_passes():
    validate_parks(_one_park())


def test_every_tag_vocab_tag_is_accepted():
    validate_parks(_one_park(tags="|".join(TAG_VOCAB)))


@pytest.mark.parametrize("tag", ["remote", "low_crowd", "permits"])
def test_note_tags_are_rejected(tag):
    with pytest.raises(ValueError, match=rf"Park test: unknown tag '{tag}' \(not in TAG_VOCAB"):
        validate_parks(_one_park(tags=f"hiking|{tag}"))


@pytest.mark.parametrize("biome", ["cave", "coast"])
def test_biome_name_used_as_tag_is_rejected(biome):
    # The park's own biome is desert, so this is a biome name used as a tag.
    with pytest.raises(ValueError, match=rf"Park test: unknown tag '{biome}' \(not in TAG_VOCAB"):
        validate_parks(_one_park(tags=f"hiking|{biome}"))


def test_real_catalog_tags_are_all_in_tag_vocab():
    parks = pd.read_csv(DATA_PATH)
    bad = sorted(
        (code, tag)
        for code, raw in zip(parks["park_code"], parks["tags"])
        for tag in parse_tags(raw)
        if tag not in TAG_VOCAB
    )
    assert bad == []


@pytest.mark.parametrize(
    "raw, message",
    [
        ("", "peak_months is empty"),
        ("4,13", "bad peak_months token '13'"),
        ("4,x", "bad peak_months token 'x'"),
        ("4,4", "peak_months repeats a month"),
    ],
)
def test_bad_peak_months_are_rejected(raw, message):
    with pytest.raises(ValueError, match=rf"Park test: {message}"):
        validate_parks(_one_park(peak_months=raw))


def test_peak_months_column_is_required():
    with pytest.raises(ValueError, match="peak_months"):
        validate_parks(_one_park().drop(columns=["peak_months"]))


def test_real_catalog_peak_months_match_nps_visits():
    from src import visits

    parks = pd.read_csv(DATA_PATH, dtype=str)
    monthly = visits.load_monthly(list(parks["park_code"]))
    for code, raw in zip(parks["park_code"], parks["peak_months"]):
        assert [int(m) for m in raw.split(",")] == visits.peak_months(monthly[code]), code
