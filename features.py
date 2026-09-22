"""Shared types and content vectors.

Content vectors contain biome + activity tags.
Common tags are down-weighted with smoothed IDF so "hiking" does not
drown out rarer signals like stargazing.

Ordinal fields are scored separately as closeness, not inside cosine.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BIOMES = [
    "alpine",
    "canyon",
    "cave",
    "chaparral",
    "coast",
    "desert",
    "forest",
    "island",
    "prairie",
    "rainforest",
    "tundra",
    "urban",
    "volcano",
    "wetland",
]

TAG_VOCAB = [
    "4x4",
    "archaeology",
    "backpacking",
    "beach",
    "bears",
    "biking",
    "birding",
    "boardwalk",
    "boat",
    "camping",
    "climbing",
    "easy_walk",
    "family",
    "fishing",
    "geothermal",
    "giant_trees",
    "glacier",
    "hiking",
    "history",
    "hot_springs",
    "kayak",
    "paleontology",
    "photography",
    "sand",
    "scenic_drive",
    "snorkeling",
    "stargazing",
    "sunrise",
    "water",
    "waterfalls",
    "wilderness",
    "wildflowers",
    "wildlife",
    "winter",
]

DAYS_ORD = {"1": 0.0, "2-3": 1.0, "4-7": 2.0, "7+": 3.0}
DIFF_ORD = {"easy": 0.0, "moderate": 1.0, "challenging": 2.0}
BUDGET_ORD = {"low": 0.0, "mid": 1.0, "high": 2.0}
CROWD_RANK = {"low": 0, "medium": 1, "high": 2}

# Great-circle miles * detour / highway speed.
# 65 mph and 1.25 detour ~= 52 mph over the crow-flies distance.
DRIVE_DETOUR = 1.25
DRIVE_MPH = 65.0


def parse_tags(raw: str) -> list[str]:
    return [part.strip() for part in str(raw).split("|") if part.strip()]


def parse_months(raw: str) -> set[str]:
    return {part.strip() for part in str(raw).split(",") if part.strip()}


def tag_idf(tag_series: pd.Series) -> np.ndarray:
    n = max(len(tag_series), 1)
    counts = np.zeros(len(TAG_VOCAB), dtype=float)
    index = {name: i for i, name in enumerate(TAG_VOCAB)}
    for raw in tag_series:
        for tag in set(parse_tags(raw)):
            if tag in index:
                counts[index[tag]] += 1.0
    return np.log((n + 1.0) / (counts + 1.0))


def _multi_hot(values: list[str], vocab: list[str]) -> np.ndarray:
    index = {name: i for i, name in enumerate(vocab)}
    vec = np.zeros(len(vocab), dtype=float)
    for item in values:
        if item in index:
            vec[index[item]] = 1.0
    return vec


def content_vector_from_parts(
    biomes: list[str],
    tags: list[str],
    idf: np.ndarray | None = None,
) -> np.ndarray:
    tag_vec = _multi_hot(tags, TAG_VOCAB)
    if idf is not None:
        tag_vec = tag_vec * idf
    return np.concatenate([_multi_hot(biomes, BIOMES), tag_vec])


def park_content_vector(row: pd.Series, idf: np.ndarray | None = None) -> np.ndarray:
    return content_vector_from_parts([str(row["biome"])], parse_tags(row["tags"]), idf=idf)


def closeness(park_level: float, user_level: float, span: float) -> float:
    """1 if identical, 0 if as far as the scale allows."""
    if span <= 0:
        return 1.0
    return 1.0 - min(abs(park_level - user_level) / span, 1.0)


def drive_hours(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_miles = 3958.8
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    miles = 2 * r_miles * np.arcsin(np.sqrt(a))
    return float(miles * DRIVE_DETOUR / DRIVE_MPH)


@dataclass
class UserProfile:
    biomes: list[str]
    tags: list[str]
    difficulty: str = "easy"
    days_needed: str = "2-3"
    crowd_pref: str = "medium"
    budget_tier: str = "mid"
    month: int | None = None
    origin_lat: float | None = None
    origin_lon: float | None = None
    max_drive_hours: float | None = None
    allow_remote: bool = True
    allow_permits: bool = True

    def content_vector(self, idf: np.ndarray | None = None) -> np.ndarray:
        return content_vector_from_parts(self.biomes, self.tags, idf=idf)
