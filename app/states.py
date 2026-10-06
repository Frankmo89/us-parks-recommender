"""Choices for the quiz's "Which states?" box. Pure helpers, no Streamlit calls."""

from __future__ import annotations

import pandas as pd

from src.features import STATE_CODES, parse_states

STATE_NAMES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DC": "District of Columbia", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine", "MI": "Michigan", "MN": "Minnesota",
    "MO": "Missouri", "MS": "Mississippi", "MT": "Montana", "NC": "North Carolina",
    "ND": "North Dakota", "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VA": "Virginia",
    "VT": "Vermont", "WA": "Washington", "WI": "Wisconsin", "WV": "West Virginia",
    "WY": "Wyoming", "AS": "American Samoa", "GU": "Guam", "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico", "VI": "U.S. Virgin Islands",
}


def state_choices(parks: pd.DataFrame) -> list[str]:
    """Codes that have at least one park in the catalog, sorted by state name.

    The engine accepts any code in STATE_CODES; the app only offers codes that
    can match, so picking one never empties the results on its own.
    """
    present = {code for raw in parks["states"] for code in parse_states(raw)}
    return sorted((code for code in present if code in STATE_CODES), key=lambda code: STATE_NAMES[code])


def state_label(code: str) -> str:
    return f"{STATE_NAMES.get(code, code)} ({code})"


def states_filter(picked: list[str] | None) -> list[str] | None:
    """Empty selection = no state filter (None)."""
    return list(picked) if picked else None
