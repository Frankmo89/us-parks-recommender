"""Import Google Form CSV exports into data/eval_profiles.json as external labels.

See docs/label-form.md for question text and choice mappings.
Appends only; never edits existing profiles or their relevant lists.
External split is for testing only — never tune on it.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import (  # noqa: E402
    BIOMES,
    TAG_VOCAB,
    InvalidProfileError,
    UserProfile,
    drive_hours,
    validate_profile,
)
from src.origins import ORIGINS  # noqa: E402
from src.recommender import ParkRecommender  # noqa: E402

PROFILES_PATH = ROOT / "data" / "eval_profiles.json"
PARKS_CSV = ROOT / "data" / "parks.csv"

# Plain-English form labels → engine tokens (must match docs/label-form.md).
BIOME_FROM_LABEL = {
    "Mountains / alpine": "alpine",
    "Canyon": "canyon",
    "Cave": "cave",
    "Chaparral / scrub": "chaparral",
    "Coast": "coast",
    "Desert": "desert",
    "Forest": "forest",
    "Island": "island",
    "Prairie / grassland": "prairie",
    "Rainforest": "rainforest",
    "Tundra": "tundra",
    "Urban": "urban",
    "Volcano": "volcano",
    "Wetland": "wetland",
}
# Also accept raw engine tokens.
BIOME_FROM_LABEL.update({b: b for b in BIOMES})

TAG_FROM_LABEL = {
    "4x4 / off-road": "4x4",
    "Archaeology": "archaeology",
    "Backpacking": "backpacking",
    "Beach": "beach",
    "Bears": "bears",
    "Biking": "biking",
    "Birding": "birding",
    "Boardwalk": "boardwalk",
    "Boat": "boat",
    "Camping": "camping",
    "Climbing": "climbing",
    "Easy walk": "easy_walk",
    "Family-friendly": "family",
    "Fishing": "fishing",
    "Geothermal": "geothermal",
    "Giant trees": "giant_trees",
    "Glacier": "glacier",
    "Hiking": "hiking",
    "History": "history",
    "Hot springs": "hot_springs",
    "Kayak": "kayak",
    "Paleontology": "paleontology",
    "Photography": "photography",
    "Sand dunes": "sand",
    "Scenic drive": "scenic_drive",
    "Snorkeling": "snorkeling",
    "Stargazing": "stargazing",
    "Sunrise / sunset views": "sunrise",
    "Water / lakes": "water",
    "Waterfalls": "waterfalls",
    "Wilderness": "wilderness",
    "Wildflowers": "wildflowers",
    "Wildlife": "wildlife",
    "Winter activities": "winter",
}
TAG_FROM_LABEL.update({t: t for t in TAG_VOCAB})

DIFFICULTY_FROM_LABEL = {
    "Easy": "easy",
    "Moderate": "moderate",
    "Challenging": "challenging",
    "easy": "easy",
    "moderate": "moderate",
    "challenging": "challenging",
}
DAYS_FROM_LABEL = {
    "Day trip": "1",
    "Weekend (2–3 days)": "2-3",
    "Weekend (2-3 days)": "2-3",
    "About a week (4–7 days)": "4-7",
    "About a week (4-7 days)": "4-7",
    "Longer than a week": "7+",
    "1": "1",
    "2-3": "2-3",
    "4-7": "4-7",
    "7+": "7+",
}
CROWD_FROM_LABEL = {
    "Prefer quiet / low crowds": "low",
    "Medium is fine": "medium",
    "Busy / popular is fine": "high",
    "low": "low",
    "medium": "medium",
    "high": "high",
}
BUDGET_FROM_LABEL = {
    "Low": "low",
    "Mid": "mid",
    "High": "high",
    "low": "low",
    "mid": "mid",
    "high": "high",
}
MONTH_FROM_LABEL = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
    "No preference / not sure": None,
    "No preference": None,
    "": None,
}
ORIGIN_FROM_LABEL = {
    "San Diego": "san_diego",
    "Los Angeles": "los_angeles",
    "Phoenix": "phoenix",
    "Denver": "denver",
    "Seattle": "seattle",
    "Salt Lake City": "salt_lake",
    "New York City": "nyc",
    "Anywhere": None,
}
ORIGIN_FROM_LABEL.update({k: k for k in ORIGINS})

YES_NO = {
    "Yes": True,
    "No": False,
    "yes": True,
    "no": False,
    "true": True,
    "false": False,
    "True": True,
    "False": False,
}

COL_TIMESTAMP = "Timestamp"
COL_TERRAINS = "Terrains you want"
COL_ACTIVITIES = "Activities you want"
COL_DIFFICULTY = "Difficulty"
COL_DAYS = "Trip length"
COL_CROWD = "Crowd preference"
COL_BUDGET = "Budget"
COL_MONTH = "Month you want to go"
COL_CITY = "Starting city"
COL_HOURS = "Max drive hours"
COL_REMOTE = "Allow remote parks"
COL_PERMITS = "Allow parks that need permits"
COL_TOP3 = "Top 3 parks"

REQUIRED_COLUMNS = [
    COL_TERRAINS,
    COL_ACTIVITIES,
    COL_DIFFICULTY,
    COL_DAYS,
    COL_CROWD,
    COL_BUDGET,
    COL_CITY,
    COL_REMOTE,
    COL_PERMITS,
    COL_TOP3,
]


def _load_park_name_to_code() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with PARKS_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            code = row["park_code"].strip()
            name = row["name"].strip()
            mapping[name] = code
            mapping[name.casefold()] = code
            mapping[code] = code
            mapping[code.casefold()] = code
    return mapping


def _split_multi(raw: str | None) -> list[str]:
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []
    parts = re.split(r"\s*[;,]\s*", text)
    return [p.strip() for p in parts if p.strip()]


def _map_list(raw: str | None, mapping: dict[str, str], field: str) -> list[str]:
    out: list[str] = []
    for part in _split_multi(raw):
        if part not in mapping:
            raise ValueError(f"Unknown {field} choice: {part!r}")
        token = mapping[part]
        if token not in out:
            out.append(token)
    return out


def _map_one(raw: str | None, mapping: dict[str, object], field: str, *, required: bool):
    text = "" if raw is None else str(raw).strip()
    if not text:
        if required:
            raise ValueError(f"Missing required field: {field}")
        return mapping.get("", None) if "" in mapping else None
    if text not in mapping:
        raise ValueError(f"Unknown {field} choice: {text!r}")
    return mapping[text]


def _parse_month(raw: str | None) -> int | None:
    text = "" if raw is None else str(raw).strip()
    if not text or text in MONTH_FROM_LABEL and MONTH_FROM_LABEL[text] is None:
        return None
    if text in MONTH_FROM_LABEL:
        return MONTH_FROM_LABEL[text]
    if text.isdigit():
        value = int(text)
        if 1 <= value <= 12:
            return value
    raise ValueError(f"Unknown month choice: {text!r}")


def _parse_hours(raw: str | None) -> float | None:
    text = "" if raw is None else str(raw).strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"Invalid max drive hours: {text!r}") from exc
    return value


def _parse_top3(raw: str | None, name_to_code: dict[str, str]) -> list[str]:
    parts = _split_multi(raw)
    if len(parts) != 3:
        raise ValueError(f"Top 3 parks must have exactly 3 picks, got {len(parts)}: {parts!r}")
    codes: list[str] = []
    for part in parts:
        key = part if part in name_to_code else part.casefold()
        if key not in name_to_code:
            raise ValueError(f"Unknown park name: {part!r}")
        code = name_to_code[key]
        if code in codes:
            raise ValueError(f"Duplicate park in top 3: {part!r}")
        codes.append(code)
    return codes


def _stable_id(timestamp: str, row_index: int, existing: set[str]) -> str:
    stamp = re.sub(r"[^0-9]", "", timestamp)[:14] or f"row{row_index:04d}"
    base = f"external_{stamp}"
    if base not in existing:
        return base
    suffix = 2
    while f"{base}_{suffix}" in existing:
        suffix += 1
    return f"{base}_{suffix}"


def pick_filter_reasons(profile: UserProfile, park_row) -> list[str]:
    """Return every hard-filter reason this park fails for the profile."""
    reasons: list[str] = []
    if not profile.allow_remote and int(park_row.remote) == 1:
        reasons.append("remote")
    if not profile.allow_permits and int(park_row.permit_likely) == 1:
        reasons.append("permit")
    if (
        profile.origin_lat is not None
        and profile.origin_lon is not None
        and profile.max_drive_hours is not None
    ):
        hours = drive_hours(
            profile.origin_lat,
            profile.origin_lon,
            float(park_row.lat),
            float(park_row.lon),
        )
        if hours > profile.max_drive_hours:
            reasons.append("drive")
    return reasons


def split_reachable_picks(
    model: ParkRecommender,
    profile: UserProfile,
    picks: list[str],
) -> tuple[list[str], list[dict]]:
    """Keep picks that pass candidates(); move the rest to unreachable with reasons.

    unreachable entries: {"park_code": str, "reasons": ["drive"|"remote"|"permit", ...]}
    """
    candidate_codes = set(model.candidates(profile)["park_code"].astype(str))
    parks_by_code = {
        str(row.park_code): row for row in model.parks.itertuples(index=False)
    }
    relevant: list[str] = []
    unreachable: list[dict] = []
    for code in picks:
        if code in candidate_codes:
            relevant.append(code)
            continue
        row = parks_by_code.get(code)
        if row is None:
            raise ValueError(f"Unknown park_code in picks: {code!r}")
        reasons = pick_filter_reasons(profile, row)
        if not reasons:
            # Should not happen if candidates() and reason checks agree.
            reasons = ["drive"]
        unreachable.append({"park_code": code, "reasons": reasons})
    return relevant, unreachable


def row_to_profile(
    row: dict[str, str],
    *,
    row_index: int,
    name_to_code: dict[str, str],
    existing_ids: set[str],
    model: ParkRecommender,
) -> dict:
    biomes = _map_list(row.get(COL_TERRAINS), BIOME_FROM_LABEL, "biome")
    tags = _map_list(row.get(COL_ACTIVITIES), TAG_FROM_LABEL, "tag")
    difficulty = _map_one(row.get(COL_DIFFICULTY), DIFFICULTY_FROM_LABEL, "difficulty", required=True)
    days_needed = _map_one(row.get(COL_DAYS), DAYS_FROM_LABEL, "days_needed", required=True)
    crowd_pref = _map_one(row.get(COL_CROWD), CROWD_FROM_LABEL, "crowd_pref", required=True)
    budget_tier = _map_one(row.get(COL_BUDGET), BUDGET_FROM_LABEL, "budget_tier", required=True)
    month = _parse_month(row.get(COL_MONTH))
    origin_key = _map_one(row.get(COL_CITY), ORIGIN_FROM_LABEL, "starting city", required=True)
    max_drive_hours = _parse_hours(row.get(COL_HOURS))
    allow_remote = _map_one(row.get(COL_REMOTE), YES_NO, "allow remote", required=True)
    allow_permits = _map_one(row.get(COL_PERMITS), YES_NO, "allow permits", required=True)
    relevant = _parse_top3(row.get(COL_TOP3), name_to_code)

    if origin_key is None:
        origin_lat = None
        origin_lon = None
        max_drive_hours = None
    else:
        origin_lat, origin_lon = ORIGINS[origin_key]
        if max_drive_hours is None:
            raise ValueError("Max drive hours is required when Starting city is not Anywhere")

    profile = UserProfile(
        biomes=biomes,
        tags=tags,
        difficulty=difficulty,
        days_needed=days_needed,
        crowd_pref=crowd_pref,
        budget_tier=budget_tier,
        month=month,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        max_drive_hours=max_drive_hours,
        allow_remote=bool(allow_remote),
        allow_permits=bool(allow_permits),
    )
    validate_profile(profile)

    payload = {
        "biomes": list(profile.biomes),
        "tags": list(profile.tags),
        "difficulty": profile.difficulty,
        "days_needed": profile.days_needed,
        "crowd_pref": profile.crowd_pref,
        "budget_tier": profile.budget_tier,
        "month": profile.month,
        "allow_remote": profile.allow_remote,
        "allow_permits": profile.allow_permits,
    }
    if profile.origin_lat is not None and profile.origin_lon is not None:
        payload["origin_lat"] = profile.origin_lat
        payload["origin_lon"] = profile.origin_lon
        payload["max_drive_hours"] = profile.max_drive_hours

    picks = relevant
    relevant, unreachable = split_reachable_picks(model, profile, picks)
    if not relevant:
        detail = ", ".join(
            f"{u['park_code']}:{'+'.join(u['reasons'])}" for u in unreachable
        )
        raise ValueError(
            f"No top-3 picks pass hard filters (all unreachable: {detail})"
        )

    profile_id = _stable_id(row.get(COL_TIMESTAMP, ""), row_index, existing_ids)
    item = {
        "id": profile_id,
        "split": "external",
        "profile": payload,
        "relevant": relevant,
    }
    if unreachable:
        item["unreachable"] = unreachable
    return item


def import_csv(
    csv_path: Path,
    *,
    profiles_path: Path = PROFILES_PATH,
    dry_run: bool = False,
) -> dict:
    name_to_code = _load_park_name_to_code()
    bundle = json.loads(profiles_path.read_text(encoding="utf-8"))
    existing = list(bundle.get("profiles") or [])
    existing_ids = {p["id"] for p in existing}
    model = ParkRecommender()

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise SystemExit("CSV has no header row")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise SystemExit(f"CSV missing required columns: {missing}")

        appended: list[dict] = []
        skipped: list[str] = []
        for index, row in enumerate(reader, start=2):  # row 1 = header
            try:
                item = row_to_profile(
                    row,
                    row_index=index,
                    name_to_code=name_to_code,
                    existing_ids=existing_ids | {a["id"] for a in appended},
                    model=model,
                )
            except (ValueError, InvalidProfileError) as exc:
                skipped.append(f"row {index}: {exc}")
                continue
            if item["id"] in existing_ids:
                skipped.append(f"row {index}: id {item['id']!r} already exists; skipped")
                continue
            appended.append(item)

    if not dry_run and appended:
        bundle["profiles"] = existing + appended
        profiles_path.write_text(
            json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {
        "appended": appended,
        "skipped": skipped,
        "n_existing": len(existing),
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Google Form CSV export path")
    parser.add_argument(
        "--profiles",
        type=Path,
        default=PROFILES_PATH,
        help="Path to eval_profiles.json (default: data/eval_profiles.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing",
    )
    args = parser.parse_args(argv)

    result = import_csv(args.csv_path, profiles_path=args.profiles, dry_run=args.dry_run)
    print(
        f"existing={result['n_existing']}  appended={len(result['appended'])}  "
        f"skipped={len(result['skipped'])}  dry_run={result['dry_run']}"
    )
    for item in result["appended"]:
        unreachable = item.get("unreachable") or []
        extra = f"  unreachable={unreachable}" if unreachable else ""
        print(f"  + {item['id']}: relevant={item['relevant']}{extra}")
    for msg in result["skipped"]:
        print(f"  ! {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
