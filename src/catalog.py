"""Validate parks.csv at catalog load time.

Scoring ignores tags outside TAG_VOCAB, so the catalog rejects them: every
tag must be a scored TAG_VOCAB tag. Unknown tokens fail loudly at load time
instead of being dropped silently.
"""

from __future__ import annotations

import pandas as pd

from .features import BIOMES, STATE_CODES, TAG_VOCAB, parse_biomes, parse_months, parse_states, parse_tags

# Tags must be scored activity tags. Biome names belong in `biomes`;
# remoteness, crowds and permits live in their own columns.
KNOWN_TAGS = frozenset(TAG_VOCAB)
KNOWN_BIOMES = set(BIOMES)

# How a traveler from the U.S. mainland reaches the park:
#   road   - drive all the way in
#   boat   - drive to a port, then a ferry/boat (drive filter uses park coords)
#   flight - needs a flight (Hawaii, territories, fly-in Alaska parks)
ACCESS_VALUES = ("road", "boat", "flight")


def validate_parks(parks: pd.DataFrame) -> None:
    """Raise ValueError naming the bad park_code if a row is invalid."""
    required = {"park_code", "states", "biomes", "tags", "best_months", "peak_months", "access"}
    missing = required - set(parks.columns)
    if missing:
        raise ValueError(f"parks catalog missing columns: {sorted(missing)}")

    for row in parks.itertuples(index=False):
        code = getattr(row, "park_code", "?")
        biomes = parse_biomes(getattr(row, "biomes", ""))
        if not biomes:
            raise ValueError(f"Park {code}: biomes is empty")
        for biome in biomes:
            if biome not in KNOWN_BIOMES:
                raise ValueError(f"Park {code}: unknown biome {biome!r}")

        tags = parse_tags(getattr(row, "tags", ""))
        biome_set = set(biomes)
        for biome in biomes:
            if biome in tags:
                raise ValueError(
                    f"Park {code}: tags must not repeat the park biome {biome!r}"
                )
        for tag in tags:
            if tag not in KNOWN_TAGS:
                raise ValueError(
                    f"Park {code}: unknown tag {tag!r} (not in TAG_VOCAB, so scoring would ignore it)"
                )

        states = parse_states(getattr(row, "states", ""))
        if not states:
            raise ValueError(f"Park {code}: states is empty")
        for state in states:
            if state not in STATE_CODES:
                raise ValueError(f"Park {code}: unknown state code {state!r}")

        access = getattr(row, "access", None)
        if not isinstance(access, str) or access not in ACCESS_VALUES:
            raise ValueError(
                f"Park {code}: access must be one of {list(ACCESS_VALUES)}, got {access!r}"
            )

        raw_months = getattr(row, "best_months", "")
        tokens = parse_months(raw_months)
        if not tokens and str(raw_months).strip():
            raise ValueError(f"Park {code}: best_months did not parse: {raw_months!r}")
        for token in tokens:
            if not token.isdigit() or not (1 <= int(token) <= 12):
                raise ValueError(f"Park {code}: bad best_months token {token!r}")

        # Peak-visitation months (NPS visits >= 0.7 x the busiest month). The
        # busiest month always qualifies, so the list is never empty.
        raw_peak = getattr(row, "peak_months", "")
        raw_peak = "" if pd.isna(raw_peak) else str(raw_peak)
        peak = [part.strip() for part in raw_peak.split(",") if part.strip()]
        if not peak:
            raise ValueError(f"Park {code}: peak_months is empty")
        for token in peak:
            if not token.isdigit() or not (1 <= int(token) <= 12):
                raise ValueError(f"Park {code}: bad peak_months token {token!r}")
        if len(set(peak)) != len(peak):
            raise ValueError(f"Park {code}: peak_months repeats a month")
