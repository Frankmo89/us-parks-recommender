"""Export catalog, weights, vocab, and ordinals for non-Python consumers.

Every value is imported from the live, validated Python engine — nothing is
hand-copied from parks.csv. Run:

    python scripts/export_engine_data.py

Writes web/engine_data.json. CI fails if that file drifts from a fresh export.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from app.breakdown import nps_url
from src.features import (
    BIOMES,
    BUDGET_ORD,
    CROWD_RANK,
    DAYS_ORD,
    DIFF_ORD,
    DRIVE_DETOUR,
    DRIVE_MPH,
    EARTH_RADIUS_MILES,
    TAG_VOCAB,
    parse_biomes,
    parse_months,
    parse_tags,
)
from src.recommender import (
    CROWD_PENALTY,
    DATA_PATH,
    MONTH_DISTANCE_MAX,
    TIE_EPSILON,
    W_BUDGET,
    W_CONTENT,
    W_DAYS,
    W_DIFF,
    W_MONTH_PENALTY,
    ParkRecommender,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "web" / "engine_data.json"


def engine_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def content_hash(csv_path: Path = DATA_PATH) -> str:
    return hashlib.sha256(csv_path.read_bytes()).hexdigest()


def build_export() -> dict:
    model = ParkRecommender()
    idf = model.idf  # same array recommend() uses
    tag_idf_map = {tag: float(idf[i]) for i, tag in enumerate(TAG_VOCAB)}

    catalog = []
    for _, row in model.parks.iterrows():
        code = str(row["park_code"])
        catalog.append(
            {
                "park_code": code,
                "name": str(row["name"]),
                "states": str(row["states"]),
                "biomes": parse_biomes(row["biomes"]),
                "tags": parse_tags(row["tags"]),
                "difficulty": str(row["difficulty"]),
                "days_needed": str(row["days_needed"]),
                "crowd": str(row["crowd"]),
                "budget_tier": str(row["budget_tier"]),
                "best_months": sorted(parse_months(row["best_months"]), key=int),
                "remote": bool(int(row["remote"])),
                "permit_likely": bool(int(row["permit_likely"])),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "nps_url": nps_url(code),
            }
        )

    return {
        "engine_version": engine_version(),
        "content_hash": content_hash(),
        "weights": {
            "W_CONTENT": W_CONTENT,
            "W_DAYS": W_DAYS,
            "W_DIFF": W_DIFF,
            "W_BUDGET": W_BUDGET,
            "CROWD_PENALTY": CROWD_PENALTY,
            "W_MONTH_PENALTY": W_MONTH_PENALTY,
            "TIE_EPSILON": TIE_EPSILON,
            "MONTH_DISTANCE_MAX": MONTH_DISTANCE_MAX,
            "DRIVE_MPH": DRIVE_MPH,
            "DRIVE_DETOUR": DRIVE_DETOUR,
            "EARTH_RADIUS_MILES": EARTH_RADIUS_MILES,
        },
        "vocab": {
            "biomes": list(BIOMES),
            "tags": list(TAG_VOCAB),
            "tag_idf": tag_idf_map,
        },
        "ordinals": {
            "days": dict(DAYS_ORD),
            "difficulty": dict(DIFF_ORD),
            "budget": dict(BUDGET_ORD),
            "crowd": {key: int(value) for key, value in CROWD_RANK.items()},
        },
        "catalog": catalog,
    }


def main() -> None:
    payload = build_export()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(payload['catalog'])} parks, v{payload['engine_version']})")


if __name__ == "__main__":
    main()
