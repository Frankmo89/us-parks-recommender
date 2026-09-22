from src.evaluate import ndcg_at_k, r_precision
from src.features import UserProfile, closeness, drive_hours
from src.recommender import ParkRecommender


def test_catalog_has_63_parks():
    model = ParkRecommender()
    assert len(model.parks) == 63
    assert model.parks["park_code"].is_unique


def test_closeness_prefers_same_bin():
    assert closeness(2.0, 2.0, 3.0) == 1.0
    assert closeness(2.0, 2.0, 3.0) > closeness(3.0, 2.0, 3.0)
    assert closeness(0.0, 0.0, 3.0) == 1.0


def test_desert_profile_returns_desert_parks():
    model = ParkRecommender()
    ranked = model.recommend(
        UserProfile(biomes=["desert"], tags=["hiking"], month=11, allow_remote=False),
        k=5,
    )
    assert not ranked.empty
    assert "desert" in set(ranked["biome"])


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
