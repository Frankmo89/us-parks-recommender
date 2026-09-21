from src.features import UserProfile
from src.recommender import ParkRecommender


def test_catalog_has_63_parks():
    model = ParkRecommender()
    assert len(model.parks) == 63
    assert model.parks["park_code"].is_unique


def test_desert_profile_returns_desert_parks():
    model = ParkRecommender()
    ranked = model.recommend(
        UserProfile(biomes=["desert"], tags=["hiking"], month=11, allow_remote=False),
        k=5,
    )
    assert not ranked.empty
    assert "desert" in set(ranked["biome"])
