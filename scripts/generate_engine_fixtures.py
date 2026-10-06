"""Regenerate data/engine_fixtures.json from the live Python engine.

The profile list is defined here: every eval profile's inputs from
data/eval_profiles.json (never its frozen ``relevant`` labels), then the
EDGE_PROFILES below. Each profile's ``output`` block and the version stamps
come from ``ParkRecommender.recommend()``.

Run after an intentional, version-bumped engine change
(docs/engine-contract.md §4):

    python scripts/generate_engine_fixtures.py
    python scripts/generate_engine_fixtures.py --check   # exit 1 on drift
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.breakdown import match_percent, nps_url  # noqa: E402
from src.evaluate import PROFILE_FIELDS  # noqa: E402
from src.features import UserProfile, parse_biomes, parse_tags  # noqa: E402
from src.recommender import (  # noqa: E402
    CROWD_PENALTY,
    TIE_EPSILON,
    W_BUDGET,
    W_CONTENT,
    W_DAYS,
    W_DIFF,
    W_MONTH_PENALTY,
    ParkRecommender,
)

FIXTURES_PATH = ROOT / "data" / "engine_fixtures.json"
EVAL_PROFILES_PATH = ROOT / "data" / "eval_profiles.json"
K = 5

# Every fixture profile carries all fields in this order (null when unset).
PROFILE_ORDER = (
    "biomes",
    "tags",
    "difficulty",
    "days_needed",
    "crowd_pref",
    "budget_tier",
    "month",
    "origin_lat",
    "origin_lon",
    "max_drive_hours",
    "allow_remote",
    "allow_permits",
    "states",
)

EVAL_NOTES = "From data/eval_profiles.json; relevant list is frozen and not part of the engine API."

# Edge cases pinned for parity. Append new ones at the end.
EDGE_PROFILES: list[dict] = [
    {
        "id": "empty_content_defaults",
        "notes": "Empty biomes/tags; all ordinal defaults. Checks defaults and content=0 handling.",
        "profile": {
            "biomes": [],
            "tags": [],
            "difficulty": "easy",
            "days_needed": "2-3",
            "crowd_pref": "medium",
            "budget_tier": "mid",
            "month": None,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": True,
            "allow_permits": True,
        },
    },
    {
        "id": "vague_easy_hikes_parents",
        "notes": "LLM mapping of 'easy hikes with my parents' -> easy, family, hiking, easy_walk.",
        "profile": {
            "biomes": [],
            "tags": ["hiking", "family", "easy_walk"],
            "difficulty": "easy",
            "days_needed": "2-3",
            "crowd_pref": "medium",
            "budget_tier": "mid",
            "month": None,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": False,
            "allow_permits": True,
        },
    },
    {
        "id": "tight_drive_from_denver",
        "notes": "Hard drive filter with a short radius; may return fewer than k.",
        "profile": {
            "biomes": ["alpine", "forest"],
            "tags": ["hiking", "scenic_drive"],
            "difficulty": "moderate",
            "days_needed": "2-3",
            "crowd_pref": "medium",
            "budget_tier": "mid",
            "month": 7,
            "origin_lat": 39.74,
            "origin_lon": -104.99,
            "max_drive_hours": 3,
            "allow_remote": False,
            "allow_permits": True,
        },
    },
    {
        "id": "no_remote_no_permits_desert",
        "notes": "Both hard filters off; desert fall trip.",
        "profile": {
            "biomes": ["desert"],
            "tags": ["hiking", "stargazing"],
            "difficulty": "easy",
            "days_needed": "1",
            "crowd_pref": "low",
            "budget_tier": "low",
            "month": 11,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": False,
            "allow_permits": False,
        },
    },
    {
        "id": "month_omitted",
        "notes": "month null => month_penalty is 0 for every park.",
        "profile": {
            "biomes": ["canyon"],
            "tags": ["hiking", "photography"],
            "difficulty": "moderate",
            "days_needed": "2-3",
            "crowd_pref": "medium",
            "budget_tier": "mid",
            "month": None,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": True,
            "allow_permits": True,
        },
    },
    {
        "id": "impossible_drive_filter",
        "notes": "Drive radius too tight from NYC with no_remote; expect empty results.",
        "profile": {
            "biomes": ["desert"],
            "tags": ["hiking"],
            "difficulty": "easy",
            "days_needed": "1",
            "crowd_pref": "low",
            "budget_tier": "low",
            "month": 4,
            "origin_lat": 40.71,
            "origin_lon": -74.01,
            "max_drive_hours": 1,
            "allow_remote": False,
            "allow_permits": False,
        },
    },
    {
        "id": "challenging_backpacking_summer",
        "notes": "Challenging + backpacking + wilderness; remote allowed.",
        "profile": {
            "biomes": ["alpine", "forest"],
            "tags": ["backpacking", "wilderness", "hiking"],
            "difficulty": "challenging",
            "days_needed": "7+",
            "crowd_pref": "low",
            "budget_tier": "mid",
            "month": 8,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": True,
            "allow_permits": True,
        },
    },
    {
        "id": "null_enum_fields_use_defaults",
        "notes": "Explicit null on all enum fields = omit; uses documented defaults.",
        "profile": {
            "biomes": ["desert"],
            "tags": ["hiking", "stargazing"],
            "difficulty": None,
            "days_needed": None,
            "crowd_pref": None,
            "budget_tier": None,
            "month": 11,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": True,
            "allow_permits": True,
        },
    },
    {
        "id": "utah_canyons_states",
        "notes": "states=[\"UT\"] keeps only Utah parks; without it Death Valley, Black Canyon and Big Bend outrank Arches and Bryce.",
        "profile": {
            "biomes": ["canyon", "desert"],
            "tags": ["hiking", "photography", "stargazing"],
            "difficulty": "moderate",
            "days_needed": "4-7",
            "crowd_pref": "medium",
            "budget_tier": "mid",
            "month": 10,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": True,
            "allow_permits": True,
            "states": ["UT"],
        },
    },
    {
        "id": "pacific_northwest_states",
        "notes": "Multi-state filter states=[\"WA\", \"OR\"]: only 4 parks qualify, so fewer than k are returned.",
        "profile": {
            "biomes": ["alpine", "forest", "rainforest"],
            "tags": ["hiking", "waterfalls", "photography"],
            "difficulty": "moderate",
            "days_needed": "2-3",
            "crowd_pref": "medium",
            "budget_tier": "mid",
            "month": 8,
            "origin_lat": None,
            "origin_lon": None,
            "max_drive_hours": None,
            "allow_remote": True,
            "allow_permits": True,
            "states": ["WA", "OR"],
        },
    },
]


def bundle_notes(n_eval: int, n_edge: int) -> list[str]:
    return [
        "Parity fixtures for a future TypeScript (or other) port of the ranking engine.",
        "Generated from the Python ParkRecommender; do not hand-edit scores.",
        "Regenerate with `python scripts/generate_engine_fixtures.py` after intentional, version-bumped engine changes.",
        f"Includes the {n_eval} eval profiles plus {n_edge} edge cases. Eval 'relevant' labels are not included.",
    ]
SCORE_DP = 6
DRIVE_DP = 4

def engine_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def _r(value: float, dp: int = SCORE_DP) -> float:
    # "+ 0.0" turns -0.0 into 0.0 so negated zero penalties serialize cleanly.
    return round(float(value), dp) + 0.0


def _months(raw: object) -> list[str]:
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _drive(value: object) -> float | None:
    if value is None:
        return None
    number = float(value)
    if math.isnan(number):
        return None
    return round(number, DRIVE_DP)


def build_output(model: ParkRecommender, profile: dict, k: int, version: str) -> dict:
    payload = {key: profile[key] for key in PROFILE_FIELDS if key in profile}
    ranked = model.recommend(UserProfile(**payload), k=k)
    parks = []
    for i, row in enumerate(ranked.itertuples(index=False), start=1):
        row = row._asdict()
        facts = {
            "park_code": str(row["park_code"]),
            "name": str(row["name"]),
            "states": str(row["states"]),
            "biomes": parse_biomes(row["biomes"]),
            "tags": parse_tags(row["tags"]),
            "difficulty": str(row["difficulty"]),
            "days_needed": str(row["days_needed"]),
            "crowd": str(row["crowd"]),
            "budget_tier": str(row["budget_tier"]),
            "best_months": _months(row["best_months"]),
            "remote": bool(int(row["remote"])),
            "permit_likely": bool(int(row["permit_likely"])),
            "access": str(row["access"]),
        }
        facts["nps_url"] = nps_url(str(row["park_code"]))
        facts["why"] = str(row["why"])
        facts["drive_hours"] = _drive(row.get("drive_hours"))

        parks.append(
            {
                "rank": i,
                "score": _r(row["score"]),
                "match_percent": match_percent(row["score"]),
                "tied_with_neighbors": bool(row["tied_with_neighbors"]),
                "breakdown": {
                    "content": _r(row["content"]),
                    "days": _r(row["days_fit"]),
                    "difficulty": _r(row["diff_fit"]),
                    "budget": _r(row["budget_fit"]),
                    "crowd_penalty": _r(row["crowd_penalty"]),
                    "month_penalty": _r(row["month_penalty"]),
                    "weighted": {
                        "content": _r(W_CONTENT * row["content"]),
                        "days": _r(W_DAYS * row["days_fit"]),
                        "difficulty": _r(W_DIFF * row["diff_fit"]),
                        "budget": _r(W_BUDGET * row["budget_fit"]),
                        "crowd_penalty": _r(-row["crowd_penalty"]),
                        "month_penalty": _r(-row["month_penalty"]),
                    },
                },
                "facts": facts,
            }
        )
    return {
        "engine_version": version,
        "k": k,
        "n_returned": len(parks),
        "empty": len(parks) == 0,
        "tie_epsilon": TIE_EPSILON,
        "tie_groups": [list(group) for group in ranked.attrs.get("tie_groups", [])],
        "parks": parks,
    }


def _full_profile(raw: dict) -> dict:
    unknown = set(raw) - set(PROFILE_ORDER)
    if unknown:
        raise ValueError(f"unknown profile fields: {sorted(unknown)}")
    return {field: raw.get(field) for field in PROFILE_ORDER}


def profile_specs(eval_path: Path = EVAL_PROFILES_PATH) -> list[dict]:
    """id / kind / split / notes / profile for every fixture, in file order."""
    eval_items = json.loads(eval_path.read_text(encoding="utf-8"))["profiles"]
    specs = [
        {
            "id": item["id"],
            "kind": "eval",
            "split": item["split"],
            "notes": EVAL_NOTES,
            "profile": _full_profile(item["profile"]),
        }
        for item in eval_items
    ]
    specs += [
        {
            "id": item["id"],
            "kind": "edge",
            "split": None,
            "notes": item["notes"],
            "profile": _full_profile(item["profile"]),
        }
        for item in EDGE_PROFILES
    ]
    ids = [spec["id"] for spec in specs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate fixture profile ids")
    return specs


def build_bundle() -> dict:
    model = ParkRecommender()
    version = engine_version()
    specs = profile_specs()
    n_eval = sum(spec["kind"] == "eval" for spec in specs)
    profiles = [
        {**spec, "output": build_output(model, spec["profile"], K, version)} for spec in specs
    ]
    return {
        "notes": bundle_notes(n_eval, len(specs) - n_eval),
        "engine_version": version,
        "weights": {
            "W_CONTENT": W_CONTENT,
            "W_DAYS": W_DAYS,
            "W_DIFF": W_DIFF,
            "W_BUDGET": W_BUDGET,
            "CROWD_PENALTY": CROWD_PENALTY,
            "W_MONTH_PENALTY": W_MONTH_PENALTY,
        },
        "tie_epsilon": TIE_EPSILON,
        "k": K,
        "profiles": profiles,
    }


def render(bundle: dict) -> str:
    return json.dumps(bundle, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the file would change")
    args = parser.parse_args(argv)

    current_text = FIXTURES_PATH.read_text(encoding="utf-8") if FIXTURES_PATH.exists() else ""
    fresh_text = render(build_bundle())
    if args.check:
        if fresh_text != current_text:
            print(f"{FIXTURES_PATH} is out of date. Run: python scripts/generate_engine_fixtures.py")
            return 1
        print(f"{FIXTURES_PATH} is up to date")
        return 0
    FIXTURES_PATH.write_text(fresh_text, encoding="utf-8")
    print(f"Wrote {FIXTURES_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
