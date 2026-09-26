"""Prove web/engine_data.json can reproduce ParkRecommender.recommend().

The JSON-only scoring path below must not import scoring helpers from src/.
It uses only arithmetic on the exported dict. Live ParkRecommender output is
the expected oracle.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from src.evaluate import PROFILE_FIELDS
from src.features import UserProfile
from src.recommender import ParkRecommender

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DATA_PATH = ROOT / "web" / "engine_data.json"
FIXTURES_PATH = ROOT / "data" / "engine_fixtures.json"
TOL = 1e-6


# --- Pure JSON scoring (no src imports in this block's logic) -----------------


def _multi_hot(values: list[str], vocab: list[str]) -> list[float]:
    index = {name: i for i, name in enumerate(vocab)}
    vec = [0.0] * len(vocab)
    for item in values:
        if item in index:
            vec[index[item]] = 1.0
    return vec


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm < 1e-12:
        return list(vec)
    return [v / norm for v in vec]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _content_vector(biomes: list[str], tags: list[str], data: dict) -> list[float]:
    biome_vec = _multi_hot(biomes, data["vocab"]["biomes"])
    tag_vec = _multi_hot(tags, data["vocab"]["tags"])
    idf = data["vocab"]["tag_idf"]
    tag_weighted = [v * float(idf[tag]) for v, tag in zip(tag_vec, data["vocab"]["tags"])]
    return biome_vec + tag_weighted


def _closeness(park_level: float, user_level: float, span: float) -> float:
    if span <= 0:
        return 1.0
    return 1.0 - min(abs(park_level - user_level) / span, 1.0)


def _month_distance(requested: int, best_months: list[str]) -> int:
    if not best_months:
        return 6
    best = 6
    for token in best_months:
        other = int(token)
        delta = abs(int(requested) - other) % 12
        best = min(best, min(delta, 12 - delta))
    return best


def _drive_hours(lat1: float, lon1: float, lat2: float, lon2: float, data: dict) -> float:
    w = data["weights"]
    r_miles = float(w["EARTH_RADIUS_MILES"])
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    miles = 2 * r_miles * math.asin(math.sqrt(a))
    return float(miles * float(w["DRIVE_DETOUR"]) / float(w["DRIVE_MPH"]))


def recommend_from_export(data: dict, profile: dict, k: int = 5) -> dict:
    """Rank parks using only exported JSON. Returns scores, breakdown, ties."""
    w = data["weights"]
    ord_days = data["ordinals"]["days"]
    ord_diff = data["ordinals"]["difficulty"]
    ord_budget = data["ordinals"]["budget"]
    ord_crowd = data["ordinals"]["crowd"]

    user_biomes = list(profile.get("biomes") or [])
    user_tags = list(profile.get("tags") or [])
    difficulty = profile.get("difficulty", "easy")
    days_needed = profile.get("days_needed", "2-3")
    crowd_pref = profile.get("crowd_pref", "medium")
    budget_tier = profile.get("budget_tier", "mid")
    month = profile.get("month")
    origin_lat = profile.get("origin_lat")
    origin_lon = profile.get("origin_lon")
    max_drive_hours = profile.get("max_drive_hours")
    allow_remote = profile.get("allow_remote", True)
    allow_permits = profile.get("allow_permits", True)

    user_vec = _l2_normalize(_content_vector(user_biomes, user_tags, data))
    days_u = float(ord_days[days_needed])
    diff_u = float(ord_diff[difficulty])
    budget_u = float(ord_budget[budget_tier])
    crowd_u = float(ord_crowd[crowd_pref])

    candidates = []
    for park in data["catalog"]:
        if not allow_remote and park["remote"]:
            continue
        if not allow_permits and park["permit_likely"]:
            continue
        drive = None
        if origin_lat is not None and origin_lon is not None and max_drive_hours is not None:
            drive = _drive_hours(
                float(origin_lat),
                float(origin_lon),
                float(park["lat"]),
                float(park["lon"]),
                data,
            )
            if drive > float(max_drive_hours):
                continue

        park_vec = _l2_normalize(_content_vector(park["biomes"], park["tags"], data))
        content = _dot(park_vec, user_vec)
        days_fit = _closeness(float(ord_days[park["days_needed"]]), days_u, 3.0)
        diff_fit = _closeness(float(ord_diff[park["difficulty"]]), diff_u, 2.0)
        budget_fit = _closeness(float(ord_budget[park["budget_tier"]]), budget_u, 2.0)
        crowd_gap = max(0.0, float(ord_crowd[park["crowd"]]) - crowd_u)
        crowd_penalty = crowd_gap * float(w["CROWD_PENALTY"])
        if month is None:
            month_penalty = 0.0
        else:
            month_penalty = (
                _month_distance(int(month), park["best_months"])
                / float(w["MONTH_DISTANCE_MAX"])
                * float(w["W_MONTH_PENALTY"])
            )
        score = (
            float(w["W_CONTENT"]) * content
            + float(w["W_DAYS"]) * days_fit
            + float(w["W_DIFF"]) * diff_fit
            + float(w["W_BUDGET"]) * budget_fit
            - crowd_penalty
            - month_penalty
        )
        candidates.append(
            {
                "park_code": park["park_code"],
                "score": score,
                "content": content,
                "days_fit": days_fit,
                "diff_fit": diff_fit,
                "budget_fit": budget_fit,
                "crowd_penalty": crowd_penalty,
                "month_penalty": month_penalty,
                "drive_hours": drive,
            }
        )

    if not candidates:
        return {"parks": [], "tie_groups": []}

    # Portable tie-break matching the engine contract: score desc, then
    # park_code asc. Do not call pandas.sort_values — re-derive independently.
    candidates.sort(key=lambda row: (-float(row["score"]), str(row["park_code"])))
    ranked = candidates[:k]

    tie_epsilon = float(w["TIE_EPSILON"])
    tie_groups: list[list[str]] = []
    tied = [False] * len(ranked)
    if ranked:
        group = [ranked[0]["park_code"]]
        for i in range(1, len(ranked)):
            if abs(ranked[i - 1]["score"] - ranked[i]["score"]) <= tie_epsilon:
                group.append(ranked[i]["park_code"])
                tied[i] = True
                tied[i - 1] = True
            else:
                if len(group) > 1:
                    tie_groups.append(group)
                group = [ranked[i]["park_code"]]
        if len(group) > 1:
            tie_groups.append(group)
    for i, row in enumerate(ranked):
        row["tied_with_neighbors"] = tied[i]

    return {"parks": ranked, "tie_groups": tie_groups}


# --- Tests --------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine_data() -> dict:
    assert ENGINE_DATA_PATH.is_file(), f"missing {ENGINE_DATA_PATH}; run scripts/export_engine_data.py"
    return json.loads(ENGINE_DATA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixtures() -> dict:
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live_model() -> ParkRecommender:
    return ParkRecommender()


def test_export_has_required_keys(engine_data: dict):
    assert engine_data["engine_version"]
    assert len(engine_data["content_hash"]) == 64
    assert len(engine_data["catalog"]) == 63
    assert set(engine_data["weights"]) >= {
        "W_CONTENT",
        "W_DAYS",
        "W_DIFF",
        "W_BUDGET",
        "CROWD_PENALTY",
        "W_MONTH_PENALTY",
        "TIE_EPSILON",
        "MONTH_DISTANCE_MAX",
        "DRIVE_MPH",
        "DRIVE_DETOUR",
        "EARTH_RADIUS_MILES",
    }
    assert len(engine_data["vocab"]["tags"]) == len(engine_data["vocab"]["tag_idf"])


def test_export_json_only_matches_live_recommend_for_all_fixtures(
    engine_data: dict, fixtures: dict, live_model: ParkRecommender
):
    assert len(fixtures["profiles"]) == 25
    for item in fixtures["profiles"]:
        profile = {key: item["profile"][key] for key in PROFILE_FIELDS}
        live = live_model.recommend(UserProfile(**profile), k=fixtures["k"])
        exported = recommend_from_export(engine_data, profile, k=fixtures["k"])

        live_codes = live["park_code"].tolist() if not live.empty else []
        export_codes = [row["park_code"] for row in exported["parks"]]
        assert export_codes == live_codes, f"{item['id']}: order mismatch {export_codes} vs {live_codes}"

        live_ties = list(live.attrs.get("tie_groups", []))
        assert exported["tie_groups"] == live_ties, (
            f"{item['id']}: tie_groups {exported['tie_groups']} vs {live_ties}"
        )

        for i, row in enumerate(exported["parks"]):
            live_row = live.iloc[i]
            for key in (
                "score",
                "content",
                "days_fit",
                "diff_fit",
                "budget_fit",
                "crowd_penalty",
                "month_penalty",
            ):
                got = float(row[key if key != "content" else "content"])
                # JSON path uses same names; live frame uses content/days_fit/...
                live_key = key
                expected = float(live_row[live_key])
                assert abs(got - expected) <= TOL, (
                    f"{item['id']} {row['park_code']} {key}: {got} vs {expected}"
                )
            assert bool(row["tied_with_neighbors"]) == bool(live_row["tied_with_neighbors"])
            if row["drive_hours"] is None:
                assert math.isnan(float(live_row["drive_hours"])) or live_row["drive_hours"] is None
            else:
                assert abs(float(row["drive_hours"]) - float(live_row["drive_hours"])) <= TOL
