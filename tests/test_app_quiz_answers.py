"""The quiz keeps every answer from step to step (app/streamlit_app.py).

Streamlit deletes a widget's key once the widget is off screen. The app must
save each answer again on every run, or the results page uses the defaults.
"""

from __future__ import annotations

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.origin import drive_limit, zip_origin
from src.features import UserProfile
from src.recommender import ParkRecommender

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")

# One non-default answer per question.
ANSWERS = {
    "biomes": ["forest"],
    "tags": ["wildlife"],
    "difficulty": "challenging",
    "days": "4-7",
    "crowd": "low",
    "budget": "high",
    "month": "July",
    "zip": "98101",
}


def click(at: AppTest, label: str) -> AppTest:
    return next(b for b in at.button if b.label == label).click().run()


def result_names(at: AppTest) -> list[str]:
    """Park names on the result cards, top card first."""
    found = (re.search(r'class="park-name[^"]*">([^<]+)<', m.value) for m in at.markdown)
    return [hit.group(1) for hit in found if hit]


def expected_names(profile: UserProfile) -> list[str]:
    return list(ParkRecommender().recommend(profile, k=5)["name"])


def walk_quiz() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60).run()
    click(at, "Start")
    at.pills[0].set_value(ANSWERS["biomes"]).run()
    click(at, "Next")
    at.pills[0].set_value(ANSWERS["tags"]).run()
    click(at, "Next")
    next(s for s in at.segmented_control if s.label == "Effort").set_value(ANSWERS["difficulty"])
    next(s for s in at.segmented_control if s.label == "Days").set_value(ANSWERS["days"])
    next(s for s in at.segmented_control if s.label == "Crowds").set_value(ANSWERS["crowd"])
    next(s for s in at.segmented_control if s.label == "Budget").set_value(ANSWERS["budget"])
    at.run()
    click(at, "Next")
    at.pills[0].set_value(ANSWERS["month"]).run()
    click(at, "Next")
    at.text_input[0].set_value(ANSWERS["zip"]).run()
    return click(at, "See parks")


def test_results_match_every_answer_not_the_defaults():
    at = walk_quiz()
    assert not at.exception
    assert at.session_state.step == "results"

    origin = zip_origin(ANSWERS["zip"])
    chosen = UserProfile(
        biomes=ANSWERS["biomes"],
        tags=ANSWERS["tags"],
        difficulty=ANSWERS["difficulty"],
        days_needed=ANSWERS["days"],
        crowd_pref=ANSWERS["crowd"],
        budget_tier=ANSWERS["budget"],
        month=7,
        origin_lat=origin.lat,
        origin_lon=origin.lon,
        max_drive_hours=drive_limit(origin, 8),
        allow_remote=False,
        allow_permits=True,
    )
    defaults = UserProfile(
        biomes=["desert"],
        tags=["hiking"],
        difficulty="easy",
        days_needed="2-3",
        crowd_pref="medium",
        budget_tier="mid",
        month=11,
        allow_remote=False,
        allow_permits=True,
    )
    assert expected_names(chosen) != expected_names(defaults)
    assert result_names(at) == expected_names(chosen)
