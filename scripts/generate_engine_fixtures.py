"""Regenerate data/engine_fixtures.json from the live Python engine.

The profile list (ids, kinds, splits, notes, profile inputs) is read from the
existing fixture file and kept as is. Only each profile's ``output`` block and
the version stamps are rebuilt from ``ParkRecommender.recommend()``. Eval
``relevant`` labels are never written here.

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


def regenerate(bundle: dict) -> dict:
    model = ParkRecommender()
    version = engine_version()
    k = int(bundle["k"])
    out = dict(bundle)
    out["engine_version"] = version
    out["weights"] = {
        "W_CONTENT": W_CONTENT,
        "W_DAYS": W_DAYS,
        "W_DIFF": W_DIFF,
        "W_BUDGET": W_BUDGET,
        "CROWD_PENALTY": CROWD_PENALTY,
        "W_MONTH_PENALTY": W_MONTH_PENALTY,
    }
    out["tie_epsilon"] = TIE_EPSILON
    profiles = []
    for item in bundle["profiles"]:
        new_item = dict(item)
        new_item["output"] = build_output(model, item["profile"], k, version)
        profiles.append(new_item)
    out["profiles"] = profiles
    return out


def render(bundle: dict) -> str:
    return json.dumps(bundle, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the file would change")
    args = parser.parse_args(argv)

    current_text = FIXTURES_PATH.read_text(encoding="utf-8")
    fresh_text = render(regenerate(json.loads(current_text)))
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
