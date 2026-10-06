"""Primary button text passes WCAG AA (4.5:1) in every state (app/contrast.py)."""

from __future__ import annotations

import math
import tomllib
from pathlib import Path

import pytest

from app.contrast import (
    AA_TEXT,
    CREAM,
    DISABLED_TEXT,
    PRIMARY_BUTTON,
    card_backgrounds,
    contrast_ratio,
    hex_rgb,
    primary_button_css,
)

ROOT = Path(__file__).resolve().parents[1]


def test_contrast_ratio_matches_wcag_reference_values():
    assert math.isclose(contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0)
    assert math.isclose(contrast_ratio(hex_rgb("#777777"), (255, 255, 255)), 4.48, abs_tol=0.01)
    assert contrast_ratio(hex_rgb(CREAM), hex_rgb(CREAM)) == 1.0


def test_streamlit_default_white_text_on_cream_fails_aa():
    # What Streamlit drew before: white text on the cream primaryColor.
    assert contrast_ratio((255, 255, 255), hex_rgb(CREAM)) < AA_TEXT


@pytest.mark.parametrize("state", sorted(PRIMARY_BUTTON))
def test_enabled_primary_button_states_pass_aa(state):
    text, background = PRIMARY_BUTTON[state]
    assert contrast_ratio(hex_rgb(text), hex_rgb(background)) >= AA_TEXT


@pytest.mark.parametrize("where", sorted(card_backgrounds()))
def test_disabled_text_readable_on_card_over_any_photo(where):
    background = card_backgrounds()[where]
    assert contrast_ratio(hex_rgb(DISABLED_TEXT), background) >= AA_TEXT


def test_theme_primary_color_is_the_cream_the_ratios_assume():
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())["theme"]
    assert theme["primaryColor"].lower() == CREAM


def test_css_covers_every_state_with_those_colors():
    css = primary_button_css()
    assert 'button[data-testid="stBaseButton-primary"]' in css
    for pseudo in (":hover", ":focus-visible", ":active", ":disabled"):
        assert pseudo in css
    for text, background in PRIMARY_BUTTON.values():
        assert f"color: {text}" in css
        assert f"background: {background}" in css
    assert f"color: {DISABLED_TEXT}" in css
