"""Do the labels lean toward famous parks?

Form respondents may pick parks they have heard of rather than parks that fit
the trip. If they do, external labels reward popularity, and a model that
finds a lesser-known but better-fitting park looks wrong.

For each profile, among the parks that pass the trip's hard filters:

- pick popularity: percentile of each picked park by average annual NPS
  visits (src.visits rules), 0 = least visited candidate, 1 = most. Picks
  made at random average 0.5.
- pick fit: percentile of each picked park by content similarity to the trip
  (terrain + activities, the model's cosine). Higher means a better fit.
- top-10 share: share of picks among the 10 most visited parks nationally.

Each split gets a mean with a 95% bootstrap range (src.uncertainty), so the
hand-written labels (train + holdout) can be compared with external ones.

Usage:
    python scripts/label_bias.py                     # labels in data/eval_profiles.json
    python scripts/label_bias.py --csv export.csv    # form responses, not imported
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import uncertainty, visits  # noqa: E402
from src.evaluate import _user_profile, load_bundle  # noqa: E402
from src.recommender import ParkRecommender, _cosine_rows  # noqa: E402

TOP_N = 10


def percentiles(values: np.ndarray) -> np.ndarray:
    """Rank percentile in [0, 1]; ties share their average rank."""
    n = len(values)
    if n == 1:
        return np.array([0.5])
    order = values.argsort(kind="stable")
    ranks = np.empty(n)
    ranks[order] = np.arange(n, dtype=float)
    for value in np.unique(values):
        same = values == value
        ranks[same] = ranks[same].mean()
    return ranks / (n - 1)


def annual_visits(model: ParkRecommender) -> dict[str, float]:
    codes = model.parks["park_code"].astype(str).tolist()
    return visits.annual_visits(visits.load_monthly(codes))


def profile_stats(model: ParkRecommender, item: dict, annual: dict[str, float], top: set[str]) -> dict | None:
    """Popularity and fit percentiles of one profile's picks among its candidates."""
    profile = _user_profile(item)
    frame = model.candidates(profile)
    codes = frame["park_code"].astype(str).tolist()
    picks = [c for c in item["relevant"] if c in codes]
    if not picks or len(codes) < 2:
        return None
    pop = percentiles(np.array([annual.get(c, 0.0) for c in codes]))
    fit = percentiles(
        _cosine_rows(profile.content_vector(idf=model.idf), model.content_matrix[frame.index])
    )
    idx = [codes.index(c) for c in picks]
    return {
        "id": item["id"],
        "split": item.get("split", "train"),
        "n_candidates": len(codes),
        "picks": picks,
        "pop_pct": float(pop[idx].mean()),
        "fit_pct": float(fit[idx].mean()),
        "top_share": sum(c in top for c in picks) / len(picks),
    }


def summarize(rows: list[dict]) -> dict:
    out = {"n": len(rows)}
    for key in ("pop_pct", "fit_pct", "top_share"):
        out[key] = uncertainty.metric_summary([r[key] for r in rows])
    out["most_picked"] = Counter(c for r in rows for c in r["picks"]).most_common(5)
    return out


def analyze(items: list[dict], model: ParkRecommender | None = None) -> dict:
    """Summaries per group: hand (train + holdout) and each other split present."""
    model = model or ParkRecommender()
    annual = annual_visits(model)
    top = {c for c, _ in sorted(annual.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]}
    rows = [r for r in (profile_stats(model, it, annual, top) for it in items) if r]
    groups: dict[str, list[dict]] = {}
    for r in rows:
        name = "hand" if r["split"] in ("train", "holdout") else r["split"]
        groups.setdefault(name, []).append(r)
    return {"top_parks": sorted(top), "groups": {g: summarize(rs) for g, rs in groups.items()}, "rows": rows}


def items_from_csv(csv_path: Path) -> list[dict]:
    """Parse a form export with the importer's own rules, without writing anything."""
    spec = importlib.util.spec_from_file_location("import_form_labels", ROOT / "scripts" / "import_form_labels.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.import_csv(csv_path, dry_run=True)["appended"]


def _fmt(s: dict) -> str:
    return f"{s['mean']:.2f} [{s['ci_low']:.2f}, {s['ci_high']:.2f}]"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, help="Google Form export to check before importing")
    args = parser.parse_args(argv)

    items = load_bundle()["profiles"]
    if args.csv:
        items = items + items_from_csv(args.csv)
    result = analyze(items)

    print("Among parks that pass each trip's hard filters (random picks: popularity 0.50, fit 0.50).")
    print(f"Top {TOP_N} by NPS visits: {', '.join(result['top_parks'])}")
    print()
    print(f"{'Labels':<10} {'n':>3}  {'Pick popularity':<20} {'Pick fit':<20} {'Top-10 share':<20}")
    for name, s in result["groups"].items():
        print(f"{name:<10} {s['n']:>3}  {_fmt(s['pop_pct']):<20} {_fmt(s['fit_pct']):<20} {_fmt(s['top_share']):<20}")
    print()
    for name, s in result["groups"].items():
        picks = ", ".join(f"{code} {count}" for code, count in s["most_picked"])
        print(f"Most picked ({name}): {picks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
