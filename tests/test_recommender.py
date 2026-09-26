from src.evaluate import ndcg_at_k, r_precision
from src.features import UserProfile, closeness, drive_hours, month_distance, parse_biomes
from src.recommender import ParkRecommender


def test_catalog_has_63_parks():
    model = ParkRecommender()
    assert len(model.parks) == 63
    assert model.parks["park_code"].is_unique


def test_closeness_prefers_same_bin():
    assert closeness(2.0, 2.0, 3.0) == 1.0
    assert closeness(2.0, 2.0, 3.0) > closeness(3.0, 2.0, 3.0)
    assert closeness(0.0, 0.0, 3.0) == 1.0


def test_month_distance_is_circular():
    assert month_distance(11, "12") == 1
    assert month_distance(12, "1") == 1
    assert month_distance(6, "12") == 6
    assert month_distance(7, "5,6,7,8") == 0
    assert month_distance(1, "") == 6


def test_desert_profile_returns_desert_parks():
    model = ParkRecommender()
    ranked = model.recommend(
        UserProfile(biomes=["desert"], tags=["hiking"], month=11, allow_remote=False),
        k=5,
    )
    assert not ranked.empty
    assert any("desert" in parse_biomes(raw) for raw in ranked["biomes"])


def test_month_is_a_soft_penalty_not_a_hard_filter():
    """Off-season parks stay in the ranking; in-season parks pay less season cost."""
    model = ParkRecommender()
    # Death Valley includes November; Crater Lake is summer-only (7,8,9).
    # Under the old hard filter, crla would be dropped for month=11.
    ranked = model.recommend(
        UserProfile(
            biomes=["desert", "alpine"],
            tags=["hiking", "scenic_drive", "family"],
            difficulty="easy",
            days_needed="1",
            crowd_pref="medium",
            budget_tier="mid",
            month=11,
            allow_remote=True,
            allow_permits=True,
        ),
        k=63,
    )
    by_code = ranked.set_index("park_code")
    assert "deva" in by_code.index
    assert "crla" in by_code.index  # still returned — not hard-filtered
    assert float(by_code.loc["deva", "month_penalty"]) == 0.0
    assert float(by_code.loc["crla", "month_penalty"]) > 0.0
    assert float(by_code.loc["deva", "score"]) > float(by_code.loc["crla", "score"])


def test_month_penalty_crossover_off_season_strong_can_beat_in_season_weak():
    """Rule 8: a strong off-season content match must beat a weak in-season one."""
    model = ParkRecommender()
    ranked = model.recommend(
        UserProfile(
            biomes=["alpine"],
            tags=["wildlife", "scenic_drive", "family"],
            difficulty="easy",
            days_needed="4-7",
            crowd_pref="medium",
            budget_tier="mid",
            month=11,
            allow_remote=True,
            allow_permits=True,
        ),
        k=63,
    ).set_index("park_code")
    romo = ranked.loc["romo"]  # alpine summer park, strong content, dist=2
    sagu = ranked.loc["sagu"]  # desert winter park, weak content, dist=0
    assert float(romo["content"]) > float(sagu["content"]) + 0.25
    assert float(romo["month_penalty"]) > float(sagu["month_penalty"])
    assert float(romo["score"]) > float(sagu["score"])


def test_drive_hours_use_catalog_coordinates():
    parks = ParkRecommender().parks.set_index("park_code")
    jotr = drive_hours(32.72, -117.16, float(parks.loc["jotr", "lat"]), float(parks.loc["jotr", "lon"]))
    sagu = drive_hours(32.72, -117.16, float(parks.loc["sagu", "lat"]), float(parks.loc["sagu", "lon"]))
    assert jotr > 1.5
    assert jotr < 3.5
    assert sagu < 8.0
    assert jotr < sagu


def test_saguaro_is_inside_an_8h_san_diego_radius():
    model = ParkRecommender()
    ranked = model.recommend(
        UserProfile(
            biomes=["desert"],
            tags=["hiking", "stargazing", "family"],
            difficulty="easy",
            days_needed="2-3",
            month=11,
            origin_lat=32.72,
            origin_lon=-117.16,
            max_drive_hours=8,
            allow_remote=False,
        ),
        k=8,
    )
    codes = ranked["park_code"].tolist()
    assert "jotr" in codes
    assert "sagu" in codes


def test_r_precision_uses_relevant_size():
    assert r_precision(["a", "b", "c", "d", "e"], ["a", "b", "c", "d"]) == 1.0
    assert ndcg_at_k(["a", "x"], ["a", "b"], k=5) > 0


def _profile_from_fixture(fixture_id: str) -> UserProfile:
    import json
    from pathlib import Path

    from src.evaluate import PROFILE_FIELDS

    bundle = json.loads(Path("data/engine_fixtures.json").read_text(encoding="utf-8"))
    item = next(p for p in bundle["profiles"] if p["id"] == fixture_id)
    return UserProfile(**{k: item["profile"][k] for k in PROFILE_FIELDS})


def test_tie_groups_gaar_kova_exact_tie():
    """remote_alaska_backpack: gaar and kova share an exact score."""
    ranked = ParkRecommender().recommend(_profile_from_fixture("remote_alaska_backpack"), k=5)
    assert ranked.attrs["tie_groups"] == [["gaar", "kova"]]
    by_code = ranked.set_index("park_code")
    assert bool(by_code.loc["gaar", "tied_with_neighbors"])
    assert bool(by_code.loc["kova", "tied_with_neighbors"])
    assert float(by_code.loc["gaar", "score"]) == float(by_code.loc["kova", "score"])
    # Annotation only — order unchanged.
    assert ranked["park_code"].tolist()[:2] == ["gaar", "kova"]


def test_tie_groups_cuva_acad_near_tie():
    """beginner_family_east: cuva and acad within TIE_EPSILON, not equal."""
    from src.recommender import TIE_EPSILON

    ranked = ParkRecommender().recommend(_profile_from_fixture("beginner_family_east"), k=5)
    assert ranked.attrs["tie_groups"] == [["cuva", "acad"]]
    by_code = ranked.set_index("park_code")
    assert bool(by_code.loc["cuva", "tied_with_neighbors"])
    assert bool(by_code.loc["acad", "tied_with_neighbors"])
    gap = abs(float(by_code.loc["cuva", "score"]) - float(by_code.loc["acad", "score"]))
    assert 0 < gap <= TIE_EPSILON


def test_tie_groups_empty_content_defaults_two_groups():
    """empty_content_defaults: ever/redw and havo/viis/thro."""
    ranked = ParkRecommender().recommend(_profile_from_fixture("empty_content_defaults"), k=5)
    assert ranked.attrs["tie_groups"] == [["ever", "redw"], ["havo", "viis", "thro"]]
    tied = set(ranked.loc[ranked["tied_with_neighbors"], "park_code"])
    assert tied == {"ever", "redw", "havo", "viis", "thro"}


def test_tie_groups_empty_when_no_ties():
    ranked = ParkRecommender().recommend(_profile_from_fixture("quiet_canyon"), k=5)
    assert ranked.attrs["tie_groups"] == []
    assert not ranked["tied_with_neighbors"].any()
    assert len(ranked) == 5
