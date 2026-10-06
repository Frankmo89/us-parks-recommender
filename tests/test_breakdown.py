import math

import pandas as pd
import pytest

from app.breakdown import MAX_SCORE, match_percent, score_breakdown, why_sentence
from src.features import UserProfile
from src.recommender import W_BUDGET, W_CONTENT, W_DAYS, W_DIFF, ParkRecommender

PROFILE = UserProfile(
    biomes=["desert"],
    tags=["hiking", "stargazing"],
    difficulty="easy",
    days_needed="2-3",
    month=11,
    origin_lat=32.72,
    origin_lon=-117.16,
    max_drive_hours=8,
    allow_remote=False,
)


def _row(content=1.0, days_fit=1.0, diff_fit=1.0, budget_fit=1.0, crowd_penalty=0.0, month_penalty=0.0):
    score = (
        W_CONTENT * content
        + W_DAYS * days_fit
        + W_DIFF * diff_fit
        + W_BUDGET * budget_fit
        - crowd_penalty
        - month_penalty
    )
    return pd.Series(
        {
            "content": content,
            "days_fit": days_fit,
            "diff_fit": diff_fit,
            "budget_fit": budget_fit,
            "crowd_penalty": crowd_penalty,
            "month_penalty": month_penalty,
            "score": score,
        }
    )


def test_score_breakdown_matches_model_output():
    model = ParkRecommender()
    ranked = model.recommend(PROFILE, k=1)
    row = ranked.iloc[0]

    breakdown = score_breakdown(row)

    expected = {
        "Terrain & activities": W_CONTENT * row["content"],
        "Days": W_DAYS * row["days_fit"],
        "Effort": W_DIFF * row["diff_fit"],
        "Budget": W_BUDGET * row["budget_fit"],
        "Crowds": -row["crowd_penalty"],
        "Season": -row["month_penalty"],
    }
    for part, value in expected.items():
        got = breakdown.loc[breakdown["part"] == part, "value"].item()
        assert math.isclose(got, value, rel_tol=1e-9, abs_tol=1e-9)

    # Same total the ranker sorted on, i.e. the same number `src.cli --explain` shows.
    assert math.isclose(breakdown["value"].sum(), row["score"], rel_tol=1e-9, abs_tol=1e-9)
    assert match_percent(row["score"]) == round(float(row["score"]) / MAX_SCORE * 100)
    assert why_sentence(breakdown)  # produces a non-empty sentence


def test_perfect_park_shows_100_percent():
    row = _row(content=1.0, days_fit=1.0, diff_fit=1.0, budget_fit=1.0, crowd_penalty=0.0)
    assert math.isclose(row["score"], MAX_SCORE, rel_tol=1e-9, abs_tol=1e-9)
    assert match_percent(row["score"]) == 100


def test_zero_crowd_penalty_never_in_sentence():
    row = _row(content=0.5, days_fit=0.9, diff_fit=0.3, budget_fit=0.6, crowd_penalty=0.0)
    breakdown = score_breakdown(row)
    assert float(breakdown.loc[breakdown["part"] == "Crowds", "value"].item()) == 0.0
    assert "crowd" not in why_sentence(breakdown).lower()


# Desert hike from the quiz: Death Valley's terrain part is its biggest gain
# (+0.26 of a 0.55 ceiling), so the sentence must not say it "lost points".
DEATH_VALLEY_PROFILE = UserProfile(
    biomes=["desert"],
    tags=["hiking"],
    difficulty="easy",
    days_needed="2-3",
    budget_tier="mid",
    crowd_pref="medium",
    month=11,
)


def test_death_valley_terrain_gain_reads_partial_match_not_lost_points():
    ranked = ParkRecommender().recommend(DEATH_VALLEY_PROFILE, k=63)
    breakdown = score_breakdown(ranked.loc[ranked["park_code"] == "deva"].iloc[0])
    values = breakdown.set_index("part")["value"]

    assert round(values["Terrain & activities"], 2) == 0.26
    assert values["Terrain & activities"] == values.max()  # biggest bar on the chart
    assert why_sentence(breakdown) == "Strong fit on length and budget; partial match on terrain."


def test_positive_fit_below_strong_cutoff_is_partial_match():
    # The numbers from the bug report: terrain +0.26 of 0.55, effort half.
    row = _row(content=0.26 / W_CONTENT, days_fit=1.0, diff_fit=0.5, budget_fit=1.0)
    sentence = why_sentence(score_breakdown(row))
    assert sentence == "Strong fit on length and budget; partial match on terrain."
    assert "lost points" not in sentence


def test_strong_part_is_never_named_in_the_second_clause():
    # Terrain is strong (0.83 of its ceiling) but still has the biggest
    # absolute gap; the clause should name the weak part (effort) instead.
    row = _row(content=0.83, days_fit=1.0, diff_fit=0.5, budget_fit=1.0)
    assert why_sentence(score_breakdown(row)) == (
        "Strong fit on terrain, length, and budget; partial match on effort."
    )


def test_zero_fit_part_reads_no_match():
    row = _row(content=0.0, days_fit=1.0, diff_fit=1.0, budget_fit=1.0)
    assert why_sentence(score_breakdown(row)) == (
        "Strong fit on length, effort, and budget; no match on terrain."
    )


@pytest.mark.parametrize(
    ("penalties", "word"),
    [
        ({"crowd_penalty": 0.24}, "crowds"),
        ({"month_penalty": 0.35}, "season"),
        ({"crowd_penalty": 0.24, "content": 0.6}, "crowds"),
    ],
)
def test_negative_parts_still_say_lost_points(penalties, word):
    row = _row(**penalties)
    breakdown = score_breakdown(row)
    part = "Crowds" if word == "crowds" else "Season"
    assert breakdown.set_index("part")["value"][part] < 0
    assert why_sentence(breakdown).endswith(f"; lost points for {word}.")


def test_badge_order_matches_ranking_order():
    model = ParkRecommender()
    ranked = model.recommend(PROFILE, k=5)
    assert len(ranked) >= 2

    percents = [match_percent(row["score"]) for _, row in ranked.iterrows()]
    assert percents == sorted(percents, reverse=True)


def _ranked_row(profile: UserProfile, code: str) -> pd.Series:
    model = ParkRecommender()
    ranked = model.recommend(profile, k=len(model.parks))
    return ranked.loc[ranked["park_code"] == code].iloc[0]


def test_card_meta_boat_park_with_drive_limit_from_la():
    from app.breakdown import card_meta

    profile = UserProfile(
        biomes=["island"], tags=["kayaking"], origin_lat=34.05, origin_lon=-118.24, max_drive_hours=8
    )
    row = _ranked_row(profile, "chis")
    assert card_meta(row) == f"CA · ~{row['drive_hours']:.1f}h drive + boat"


def test_card_meta_no_drive_limit_flight_and_boat_needed():
    from app.breakdown import card_meta

    profile = UserProfile(biomes=["volcano", "island"], tags=["hiking"])
    assert card_meta(_ranked_row(profile, "havo")).endswith(" · flight needed")
    assert card_meta(_ranked_row(profile, "chis")).endswith(" · boat needed")
    # Road park with no drive limit: states only, multi-state spaced out.
    assert card_meta(_ranked_row(profile, "yell")) == "WY, MT, ID"
    assert card_meta(_ranked_row(profile, "olym")) == "WA"


def test_card_meta_road_park_with_drive_limit():
    from app.breakdown import card_meta

    row = _ranked_row(PROFILE, "jotr")
    assert card_meta(row) == f"CA · ~{row['drive_hours']:.1f}h drive"
