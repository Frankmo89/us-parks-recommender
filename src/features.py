"""Feature space shared by parks and user profiles."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

BIOMES = ["alpine","canyon","cave","chaparral","coast","desert","forest","island","prairie","rainforest","tundra","urban","volcano","wetland"]
TAG_VOCAB = ["4x4","alpine","archaeology","backpacking","beach","bears","biking","birding","boardwalk","boat","camping","canyon","cave","climbing","coast","desert","easy_walk","family","fishing","geothermal","giant_trees","glacier","hiking","history","hot_springs","kayak","low_crowd","paleontology","permits","photography","rainforest","remote","sand","scenic_drive","snorkeling","stargazing","sunrise","urban","volcano","water","waterfalls","wilderness","wildflowers","wildlife","winter"]
DIFFICULTY = ["easy","moderate","challenging"]
DAYS = ["1","2-3","4-7","7+"]
DAYS_ORD = {"1":0.0,"2-3":1.0,"4-7":2.0,"7+":3.0}
DIFF_ORD = {"easy":0.0,"moderate":1.0,"challenging":2.0}
CROWD = ["low","medium","high"]
BUDGET = ["low","mid","high"]
MONTHS = list(range(1,13))
CROWD_RANK = {"low":0,"medium":1,"high":2}

def _one_hot(value, vocab):
    vec = np.zeros(len(vocab), dtype=float)
    if value in vocab:
        vec[vocab.index(value)] = 1.0
    return vec

def _multi_hot(values, vocab):
    vec = np.zeros(len(vocab), dtype=float)
    index = {name:i for i,name in enumerate(vocab)}
    for item in values:
        if item in index:
            vec[index[item]] = 1.0
    return vec

def _parse_tags(raw):
    return [part.strip() for part in str(raw).split("|") if part.strip()]

def _parse_months(raw):
    months = []
    for part in str(raw).split(","):
        part = part.strip()
        if part.isdigit():
            month = int(part)
            if 1 <= month <= 12:
                months.append(month)
    return months

def park_vector(row):
    tags = _parse_tags(row["tags"])
    months = _parse_months(row["best_months"])
    return np.concatenate([
        _one_hot(row["biome"], BIOMES),
        _multi_hot(tags, TAG_VOCAB),
        _one_hot(row["difficulty"], DIFFICULTY),
        np.array([DIFF_ORD.get(str(row["difficulty"]),1.0)/2.0, DAYS_ORD.get(str(row["days_needed"]),1.0)/3.0], dtype=float),
        _one_hot(row["crowd"], CROWD),
        _one_hot(row["budget_tier"], BUDGET),
        _multi_hot([str(m) for m in months], [str(m) for m in MONTHS]),
        np.array([float(row["permit_likely"]), float(row["remote"])], dtype=float),
    ])

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

    def vector(self):
        month_hot = np.zeros(12, dtype=float)
        if self.month is not None and 1 <= self.month <= 12:
            month_hot[self.month-1] = 1.0
        else:
            month_hot[:] = 1.0/12
        return np.concatenate([
            _multi_hot(self.biomes, BIOMES),
            _multi_hot(self.tags, TAG_VOCAB),
            _one_hot(self.difficulty, DIFFICULTY),
            np.array([DIFF_ORD.get(self.difficulty,1.0)/2.0, DAYS_ORD.get(self.days_needed,1.0)/3.0], dtype=float),
            _one_hot(self.crowd_pref, CROWD),
            _one_hot(self.budget_tier, BUDGET),
            month_hot,
            np.array([0.0 if self.allow_permits else 1.0, 0.0 if self.allow_remote else 1.0], dtype=float),
        ])

def haversine_hours(lat1, lon1, lat2, lon2, mph=50.0):
    r_miles = 3958.8
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2-lat1)
    dlmb = np.radians(lon2-lon1)
    a = np.sin(dphi/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dlmb/2)**2
    miles = 2 * r_miles * np.arcsin(np.sqrt(a))
    return float(miles / mph)
