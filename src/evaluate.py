"""R-Precision and nDCG@K on labeled fixtures.

These are acceptance fixtures, not a published benchmark.
Train was used only to sanity-check the first weight set.
Holdout was not used to pick weights.

Baselines and ablations use the same hard-filtered candidate set as the
model so the comparison is fair. They do not change scoring.

The external split (crowd labels from docs/label-form.md) is reported on
its own lines for testing only. ``all`` stays train + holdout so legacy
numbers stay comparable. Never tune on external.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

from functools import lru_cache

from . import uncertainty, visits
from .features import UserProfile
from .recommender import ParkRecommender, _cosine_rows

PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "eval_profiles.json"

PROFILE_FIELDS = {
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
}

RANDOM_SEEDS = range(100)  # 0..99


def load_bundle(path: Path | None = None) -> dict:
    return json.loads((path or PROFILES_PATH).read_text(encoding="utf-8"))


def r_precision(recommended: list[str], relevant: list[str]) -> float:
    if not relevant:
        return 0.0
    k = len(relevant)
    hits = sum(1 for code in recommended[:k] if code in relevant)
    return hits / k


def dcg(recommended: list[str], relevant: set[str], k: int) -> float:
    total = 0.0
    for i, code in enumerate(recommended[:k], start=1):
        rel = 1.0 if code in relevant else 0.0
        total += rel / math.log2(i + 1)
    return total


def ndcg_at_k(recommended: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    ideal = dcg(relevant, set(relevant), k)
    if ideal == 0:
        return 0.0
    return dcg(recommended, set(relevant), k) / ideal


def _user_profile(item: dict) -> UserProfile:
    payload = {key: value for key, value in item["profile"].items() if key in PROFILE_FIELDS}
    return UserProfile(**payload)


def _aggregate(rows: list[dict], k: int) -> dict:
    n = max(len(rows), 1)
    return {
        "k": k,
        "n": len(rows),
        "mean_r_precision": sum(r["r_precision"] for r in rows) / n if rows else 0.0,
        "mean_ndcg_at_k": sum(r["ndcg_at_k"] for r in rows) / n if rows else 0.0,
        "profiles": rows,
    }


def _without_filter_only(block: dict) -> dict:
    kept = [row for row in block["profiles"] if not row.get("filter_only")]
    return _aggregate(kept, block["k"])


@lru_cache(maxsize=1)
def _annual_visits(codes: tuple[str, ...]) -> dict[str, float]:
    """Average annual NPS recreation visits, 2023-2025 (src.visits rules)."""
    return visits.annual_visits(visits.load_monthly(list(codes)))


def popularity_rank(model: ParkRecommender, profile: UserProfile, k: int = 5) -> list[str]:
    """Rank hard-filtered parks by average annual NPS visits, then park_code.

    Visits are the 2023-2025 average, with Oct/Nov 2025 (federal shutdown)
    taken from 2023-2024 only; see src/visits.py.
    """
    frame = model.candidates(profile)
    if frame.empty:
        return []
    annual = _annual_visits(tuple(model.parks["park_code"].astype(str)))
    ranked = frame.assign(_visits=frame["park_code"].map(annual)).sort_values(
        ["_visits", "park_code"],
        ascending=[False, True],
        kind="stable",
    )
    return ranked["park_code"].astype(str).head(k).tolist()


def content_only_rank(model: ParkRecommender, profile: UserProfile, k: int = 5) -> list[str]:
    """Rank hard-filtered parks by cosine content similarity alone."""
    frame = model.candidates(profile)
    if frame.empty:
        return []
    content = _cosine_rows(
        profile.content_vector(idf=model.idf),
        model.content_matrix[frame.index],
    )
    ranked = frame.assign(_content=content).sort_values(
        ["_content", "park_code"],
        ascending=[False, True],
        kind="stable",
    )
    return ranked["park_code"].astype(str).head(k).tolist()


def random_rank_means(
    model: ParkRecommender,
    profile: UserProfile,
    relevant: list[str],
    k: int = 5,
) -> tuple[float, float]:
    """Mean R-Precision and nDCG@k over 100 shuffles (seeds 0..99)."""
    base = sorted(model.candidates(profile)["park_code"].astype(str).tolist())
    if not base:
        return 0.0, 0.0
    r_sum = 0.0
    n_sum = 0.0
    n_seeds = 0
    for seed in RANDOM_SEEDS:
        shuffled = base.copy()
        random.Random(seed).shuffle(shuffled)
        top = shuffled[:k]
        r_sum += r_precision(top, relevant)
        n_sum += ndcg_at_k(top, relevant, k)
        n_seeds += 1
    return r_sum / n_seeds, n_sum / n_seeds


def _is_filter_only(random_r: float, random_ndcg: float) -> bool:
    """True when any ranking order scores perfectly — filters alone decide."""
    return random_r == 1.0 and random_ndcg == 1.0


def _score_profiles(
    model: ParkRecommender,
    profiles: list[dict],
    *,
    method: str,
    k: int,
    filter_only_ids: set[str],
) -> dict:
    rows = []
    for item in profiles:
        profile = _user_profile(item)
        frame = model.candidates(profile)
        n_candidates = len(frame)
        relevant = item["relevant"]
        filter_only = item["id"] in filter_only_ids

        if method == "model":
            codes = model.recommend(profile, k=k)["park_code"].tolist()
            r_prec = r_precision(codes, relevant)
            ndcg = ndcg_at_k(codes, relevant, k)
        elif method == "popularity":
            codes = popularity_rank(model, profile, k=k)
            r_prec = r_precision(codes, relevant)
            ndcg = ndcg_at_k(codes, relevant, k)
        elif method == "content_only":
            codes = content_only_rank(model, profile, k=k)
            r_prec = r_precision(codes, relevant)
            ndcg = ndcg_at_k(codes, relevant, k)
        elif method == "random":
            r_prec, ndcg = random_rank_means(model, profile, relevant, k=k)
            codes = []
        else:
            raise ValueError(f"unknown method={method!r}")

        rows.append(
            {
                "id": item["id"],
                "split": item.get("split", "train"),
                "r_precision": r_prec,
                "ndcg_at_k": ndcg,
                "n_returned": len(codes) if codes else k,
                "n_candidates": n_candidates,
                "filter_only": filter_only,
                "recommended": codes,
                "relevant": relevant,
            }
        )
    return _aggregate(rows, k)


def _detect_filter_only(
    model: ParkRecommender, profiles: list[dict], k: int
) -> set[str]:
    ids: set[str] = set()
    for item in profiles:
        profile = _user_profile(item)
        r_prec, ndcg = random_rank_means(model, profile, item["relevant"], k=k)
        if _is_filter_only(r_prec, ndcg):
            ids.add(item["id"])
    return ids



def external_unreachable_counts(profiles: list[dict]) -> dict[str, int]:
    """Count unreachable external picks by hard-filter reason."""
    counts = {"drive": 0, "remote": 0, "permit": 0, "parks": 0}
    for item in profiles:
        for entry in item.get("unreachable") or []:
            counts["parks"] += 1
            for reason in entry.get("reasons") or []:
                if reason in counts:
                    counts[reason] += 1
    return counts


BASELINES = ("content_only", "popularity", "random")
METRICS = (("r_precision", "R-Prec"), ("ndcg_at_k", "nDCG@5"))


def _scores(block: dict, metric: str) -> list[float]:
    return [row[metric] for row in block["profiles"]]


def uncertainty_report(blocks: dict[str, dict]) -> dict:
    """95% bootstrap ranges per method and paired tests of model vs each baseline.

    ``blocks`` maps method -> one scored block (same profiles, same order).
    """
    summary = {
        method: {metric: uncertainty.metric_summary(_scores(block, metric)) for metric, _ in METRICS}
        for method, block in blocks.items()
    }
    paired = {
        baseline: {
            metric: uncertainty.paired_test(_scores(blocks["model"], metric), _scores(blocks[baseline], metric))
            for metric, _ in METRICS
        }
        for baseline in BASELINES
    }
    return {"summary": summary, "model_vs": paired}


def run(k: int = 5) -> dict:
    bundle = load_bundle()
    model = ParkRecommender()
    profiles = bundle["profiles"]
    train = [p for p in profiles if p.get("split", "train") == "train"]
    holdout = [p for p in profiles if p.get("split") == "holdout"]
    external = [p for p in profiles if p.get("split") == "external"]
    # ``all`` is train + holdout only so legacy metrics stay comparable.
    comparable = train + holdout

    filter_only_ids = _detect_filter_only(model, comparable + external, k=k)

    def score_method(method: str) -> dict:
        return {
            "train": _score_profiles(
                model, train, method=method, k=k, filter_only_ids=filter_only_ids
            ),
            "holdout": _score_profiles(
                model, holdout, method=method, k=k, filter_only_ids=filter_only_ids
            ),
            "all": _score_profiles(
                model, comparable, method=method, k=k, filter_only_ids=filter_only_ids
            ),
            "external": _score_profiles(
                model, external, method=method, k=k, filter_only_ids=filter_only_ids
            ),
        }

    model_blocks = score_method("model")
    popularity = score_method("popularity")
    random_blocks = score_method("random")
    content_only = score_method("content_only")

    excl = {
        "model": {split: _without_filter_only(block) for split, block in model_blocks.items()},
        "popularity": {
            split: _without_filter_only(block) for split, block in popularity.items()
        },
        "random": {
            split: _without_filter_only(block) for split, block in random_blocks.items()
        },
        "content_only": {
            split: _without_filter_only(block) for split, block in content_only.items()
        },
    }

    methods = {"model": model_blocks, "popularity": popularity, "random": random_blocks, "content_only": content_only}
    # Train + holdout, the scope the README results use; plus the same scope
    # without filter-only profiles, where ranking can actually change the score.
    uncertainty_blocks = {
        "all": uncertainty_report({m: blocks["all"] for m, blocks in methods.items()}),
        "all_excl_filter_only": uncertainty_report({m: excl[m]["all"] for m in methods}),
    }

    return {
        # Top-level train/holdout/all stay model-only for Streamlit / existing tests.
        "train": model_blocks["train"],
        "holdout": model_blocks["holdout"],
        "all": model_blocks["all"],
        "external": model_blocks["external"],
        "popularity": popularity,
        "random": random_blocks,
        "content_only": content_only,
        "excl_filter_only": excl,
        "filter_only_ids": sorted(filter_only_ids),
        "external_unreachable": external_unreachable_counts(external),
        "uncertainty": uncertainty_blocks,
    }


def _print_block(title: str, block: dict) -> None:
    print(
        f"{title}: n={block['n']}  R-Prec={block['mean_r_precision']:.3f}  "
        f"nDCG@{block['k']}={block['mean_ndcg_at_k']:.3f}"
    )
    for row in block["profiles"]:
        fo = " [filter-only]" if row.get("filter_only") else ""
        recommended = row.get("recommended") or []
        print(
            f"  {row['id']}: candidates={row.get('n_candidates', '?')} "
            f"R={row['r_precision']:.2f} nDCG={row['ndcg_at_k']:.2f} "
            f"n={row['n_returned']}{fo}  -> {recommended}"
        )


def _print_comparison_table(result: dict) -> None:
    methods = [
        ("Model", "model", False),
        ("Model", "model", True),
        ("Popularity", "popularity", False),
        ("Popularity", "popularity", True),
        ("Random", "random", False),
        ("Random", "random", True),
        ("Content-only", "content_only", False),
        ("Content-only", "content_only", True),
    ]
    splits = ("train", "holdout", "all", "external")
    print(
        f"{'Method':<14} {'Scope':<18} {'Split':<8} {'n':>3}  "
        f"{'R-Prec':>7}  {'nDCG@5':>7}"
    )
    print("-" * 62)
    for label, key, excl in methods:
        scope = "excl. filter-only" if excl else "all"
        for split in splits:
            if excl:
                block = result["excl_filter_only"][key][split]
            elif key == "model":
                block = result[split]
            else:
                block = result[key][split]
            print(
                f"{label:<14} {scope:<18} {split:<8} {block['n']:>3}  "
                f"{block['mean_r_precision']:>7.3f}  "
                f"{block['mean_ndcg_at_k']:>7.3f}"
            )
    print()
    fo_ids = result.get("filter_only_ids") or []
    print(
        "Filter-only profiles (random R-Prec=1 and nDCG@5=1; ranking cannot change score): "
        + (", ".join(fo_ids) if fo_ids else "(none)")
    )
    unreachable = result.get("external_unreachable") or {}
    print(
        "External unreachable picks (hard filters, not ranking): "
        f"parks={unreachable.get('parks', 0)} "
        f"drive={unreachable.get('drive', 0)} "
        f"remote={unreachable.get('remote', 0)} "
        f"permit={unreachable.get('permit', 0)}"
    )


def _format_p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def _print_uncertainty(result: dict) -> None:
    labels = {"model": "Model", "content_only": "Content-only", "popularity": "Popularity", "random": "Random"}
    scopes = (("all", "train+holdout"), ("all_excl_filter_only", "train+holdout, excl. filter-only"))
    print("Uncertainty: 95% bootstrap range of the mean (10,000 resamples of profiles, seed 0)")
    for key, title in scopes:
        report = result["uncertainty"][key]
        n = report["summary"]["model"]["r_precision"]["n"]
        print(f"  {title} (n={n})")
        for method, label in labels.items():
            parts = []
            for metric, name in METRICS:
                s = report["summary"][method][metric]
                parts.append(f"{name} {s['mean']:.3f} [{s['ci_low']:.3f}, {s['ci_high']:.3f}]")
            print(f"    {label:<13} " + "   ".join(parts))
    print()
    print("Model minus baseline, same profiles (mean diff [95% range], exact sign-flip p, wins/ties/losses)")
    for key, title in scopes:
        report = result["uncertainty"][key]
        print(f"  {title}")
        for baseline in BASELINES:
            for metric, name in METRICS:
                t = report["model_vs"][baseline][metric]
                print(
                    f"    vs {labels[baseline]:<13} {name:<7} {t['mean_diff']:+.3f} "
                    f"[{t['ci_low']:+.3f}, {t['ci_high']:+.3f}]  {_format_p(t['p_value'])}  "
                    f"{t['wins']}/{t['ties']}/{t['losses']}"
                )


def main() -> None:
    result = run(k=5)
    _print_comparison_table(result)
    print()
    _print_block("train (model)", result["train"])
    print()
    _print_block("holdout (model)", result["holdout"])
    print()
    _print_block("all (model; train+holdout)", result["all"])
    print()
    _print_block("external (model; test-only)", result["external"])
    print()
    _print_uncertainty(result)


if __name__ == "__main__":
    main()
