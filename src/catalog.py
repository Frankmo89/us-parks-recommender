"""Validate parks.csv at catalog load time.

Scoring still ignores tags outside TAG_VOCAB; this check only guards data
quality so unknown tokens fail loudly instead of silently.
"""

from __future__ import annotations

import pandas as pd

from .features import BIOMES, TAG_VOCAB, parse_months, parse_tags

# Other biome names may appear as tags on a park (e.g. alpine on a forest
# park). A park's own biome must not be repeated in tags. Catalog annotations
# (low_crowd, permits, remote) are also allowed as tags but are not activity
# features — scoring ignores them via TAG_VOCAB.
KNOWN_TAGS = set(TAG_VOCAB) | set(BIOMES) | {"low_crowd", "permits", "remote"}
KNOWN_BIOMES = set(BIOMES)


def validate_parks(parks: pd.DataFrame) -> None:
    """Raise ValueError naming the bad park_code if a row is invalid."""
    required = {"park_code", "biome", "tags", "best_months"}
    missing = required - set(parks.columns)
    if missing:
        raise ValueError(f"parks catalog missing columns: {sorted(missing)}")

    for row in parks.itertuples(index=False):
        code = getattr(row, "park_code", "?")
        biome = str(getattr(row, "biome", ""))
        if biome not in KNOWN_BIOMES:
            raise ValueError(f"Park {code}: unknown biome {biome!r}")

        tags = parse_tags(getattr(row, "tags", ""))
        if biome in tags:
            raise ValueError(
                f"Park {code}: tags must not repeat the park biome {biome!r}"
            )
        for tag in tags:
            if tag not in KNOWN_TAGS:
                raise ValueError(f"Park {code}: unknown tag {tag!r}")

        raw_months = getattr(row, "best_months", "")
        tokens = parse_months(raw_months)
        if not tokens and str(raw_months).strip():
            raise ValueError(f"Park {code}: best_months did not parse: {raw_months!r}")
        for token in tokens:
            if not token.isdigit() or not (1 <= int(token) <= 12):
                raise ValueError(f"Park {code}: bad best_months token {token!r}")
