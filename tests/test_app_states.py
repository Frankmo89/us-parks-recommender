"""Quiz "Which states?" choices (app/states.py)."""

from __future__ import annotations

from app.states import STATE_NAMES, state_choices, state_label, states_filter
from src.features import STATE_CODES
from src.recommender import ParkRecommender


def test_every_state_code_has_a_name():
    assert set(STATE_NAMES) == set(STATE_CODES)


def test_choices_are_catalog_states_sorted_by_name():
    parks = ParkRecommender().parks
    choices = state_choices(parks)
    present = {code for raw in parks["states"] for code in str(raw).split(",")}
    assert set(choices) == present
    assert [STATE_NAMES[c] for c in choices] == sorted(STATE_NAMES[c] for c in choices)
    assert "UT" in choices and "DE" not in choices


def test_label_and_empty_selection():
    assert state_label("UT") == "Utah (UT)"
    assert states_filter([]) is None
    assert states_filter(None) is None
    assert states_filter(["UT", "AZ"]) == ["UT", "AZ"]
