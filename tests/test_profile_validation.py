"""Profile validation and hard-filter guarantees."""

from __future__ import annotations

import math
import random

import pytest

from src.features import (
    BUDGET_VALUES,
    CROWD_VALUES,
    DAYS_VALUES,
    DIFFICULTY_VALUES,
    InvalidProfileError,
    UserProfile,
    validate_profile,
)
from src.recommender import ParkRecommender


def test_invalid_difficulty_raises_typed_error():
    with pytest.raises(InvalidProfileError) as exc:
        validate_profile(UserProfile(biomes=["desert"], tags=["hiking"], difficulty="hard"))
    assert exc.value.field == "difficulty"
    assert exc.value.value == "hard"
    assert "easy" in str(exc.value)
    assert "Invalid difficulty='hard'" in str(exc.value)


@pytest.mark.parametrize(
    "field,value,allowed_fragment",
    [
        ("difficulty", "hard", "challenging"),
        ("days_needed", "weekend", "2-3"),
        ("crowd_pref", "quiet", "medium"),
        ("budget_tier", "cheap", "mid"),
        ("month", 0, "1-12"),
        ("month", 13, "1-12"),
        ("month", "10", "1-12"),
        ("month", 1.5, "1-12"),
        ("max_drive_hours", 0, "positive"),
        ("max_drive_hours", -3, "positive"),
        ("max_drive_hours", "eight", "positive"),
    ],
)
def test_documented_invalid_inputs_raise_with_field_name(field, value, allowed_fragment):
    kwargs = {"biomes": ["desert"], "tags": ["hiking"], field: value}
    with pytest.raises(InvalidProfileError) as exc:
        validate_profile(UserProfile(**kwargs))
    assert exc.value.field == field
    assert allowed_fragment in str(exc.value)


def test_recommend_raises_invalid_profile_not_keyerror():
    model = ParkRecommender()
    with pytest.raises(InvalidProfileError) as exc:
        model.recommend(UserProfile(biomes=["desert"], tags=["hiking"], difficulty="hard"))
    assert exc.value.field == "difficulty"
    assert not isinstance(exc.value, KeyError)


def test_unknown_biome_and_tag_do_not_raise():
    profile = UserProfile(
        biomes=["atlantis", "desert"],
        tags=["hoverboarding", "hiking"],
        difficulty="easy",
    )
    validate_profile(profile)  # must not raise
    ranked = ParkRecommender().recommend(profile, k=3)
    assert not ranked.empty


@pytest.mark.parametrize(
    "field,default",
    [
        ("difficulty", "easy"),
        ("days_needed", "2-3"),
        ("crowd_pref", "medium"),
        ("budget_tier", "mid"),
    ],
)
def test_enum_null_equals_omit(field, default):
    """Explicit None on an enum field matches omitting it (documented default)."""
    model = ParkRecommender()
    base = {"biomes": ["desert"], "tags": ["hiking", "stargazing"], "month": 11}
    omitted = UserProfile(**base)
    with_null = UserProfile(**base, **{field: None})
    validate_profile(omitted)
    validate_profile(with_null)
    assert getattr(with_null, field) == default
    assert getattr(omitted, field) == default

    a = model.recommend(UserProfile(**base), k=5)
    b = model.recommend(UserProfile(**base, **{field: None}), k=5)
    assert a["park_code"].tolist() == b["park_code"].tolist()
    assert list(a["score"]) == pytest.approx(list(b["score"]), abs=1e-12)
    assert a.attrs["tie_groups"] == b.attrs["tie_groups"]


def test_valid_defaults_and_month_null_ok():
    validate_profile(UserProfile(biomes=[], tags=[]))
    validate_profile(UserProfile(biomes=["coast"], tags=["boat"], month=None))
    validate_profile(UserProfile(biomes=["coast"], tags=["boat"], month=12, max_drive_hours=8.5))


def _random_valid_profile(rng: random.Random) -> UserProfile:
    use_drive = rng.random() < 0.5
    return UserProfile(
        biomes=rng.sample(
            ["desert", "forest", "alpine", "canyon", "coast", "wetland"],
            k=rng.randint(0, 3),
        ),
        tags=rng.sample(
            ["hiking", "family", "scenic_drive", "wildlife", "stargazing", "camping"],
            k=rng.randint(0, 4),
        ),
        difficulty=rng.choice(list(DIFFICULTY_VALUES)),
        days_needed=rng.choice(list(DAYS_VALUES)),
        crowd_pref=rng.choice(list(CROWD_VALUES)),
        budget_tier=rng.choice(list(BUDGET_VALUES)),
        month=rng.choice([None, *range(1, 13)]),
        origin_lat=41.88 if use_drive else None,
        origin_lon=-87.63 if use_drive else None,
        max_drive_hours=rng.uniform(2.0, 14.0) if use_drive else None,
        allow_remote=rng.choice([True, False]),
        allow_permits=rng.choice([True, False]),
    )


def test_hard_filters_never_violated_across_random_valid_profiles():
    model = ParkRecommender()
    rng = random.Random(20260926)
    for _ in range(40):
        profile = _random_valid_profile(rng)
        ranked = model.recommend(profile, k=63)
        if ranked.empty:
            continue
        if not profile.allow_remote:
            assert (ranked["remote"] == 0).all()
        if not profile.allow_permits:
            assert (ranked["permit_likely"] == 0).all()
        if (
            profile.origin_lat is not None
            and profile.origin_lon is not None
            and profile.max_drive_hours is not None
        ):
            assert ranked["drive_hours"].notna().all()
            assert (ranked["drive_hours"] <= profile.max_drive_hours + 1e-9).all()
            assert not ranked["drive_hours"].apply(lambda v: isinstance(v, float) and math.isnan(v)).any()
