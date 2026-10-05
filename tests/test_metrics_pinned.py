"""Pin train/holdout metrics to the values published in README.md.

Parses the Metrics table in README.md and compares those numbers to
`src.evaluate` output (rounded to 3 decimals). Hardcoded constants are not
used — if README and evaluate() disagree, the failure names which side is wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.evaluate import run

README_PATH = Path(__file__).resolve().parents[1] / "README.md"

_ROW = re.compile(
    r"^\|\s*(Model|Popularity|Random|Content-only)"
    r"(?:\s*\(excl\.\s*filter-only\))?\s*"
    r"\|\s*(Train|Holdout|All)\s*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|",
    re.MULTILINE,
)

_METHOD_BASE = {
    "model": "model",
    "popularity": "popularity",
    "random": "random",
    "content-only": "content_only",
}


def metrics_from_readme(
    text: str | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    """Parse Method × Split R-Precision and nDCG@5 from README's Metrics table.

    Keys look like ``model``, ``model_excl_filter_only``, ``content_only``, …
    """
    raw = text if text is not None else README_PATH.read_text(encoding="utf-8")
    found: dict[str, dict[str, dict[str, float]]] = {}
    for match in _ROW.finditer(raw):
        full = match.group(0)
        method_label = match.group(1)
        split = match.group(2).lower()
        r_prec = float(match.group(4))
        ndcg = float(match.group(5))
        base = _METHOD_BASE[method_label.lower()]
        excl = "excl. filter-only" in full.lower() or "excl. filter-only" in full
        # Detect excl from the matched line text between method and split.
        between = full.split("|")[1]
        key = f"{base}_excl_filter_only" if "excl" in between.lower() else base
        found.setdefault(key, {})[split] = {
            "r_precision": r_prec,
            "ndcg_at_5": ndcg,
            "n": int(match.group(3)),
        }

    required_methods = [
        "model",
        "model_excl_filter_only",
        "popularity",
        "popularity_excl_filter_only",
        "random",
        "random_excl_filter_only",
        "content_only",
        "content_only_excl_filter_only",
    ]
    for method in required_methods:
        if method not in found or not {"train", "holdout", "all"}.issubset(found[method]):
            raise AssertionError(
                "README.md Metrics table must include Model/Popularity/Random/"
                "Content-only rows (with and without excl. filter-only) for "
                f"Train/Holdout/All; parsed={ {m: sorted(s) for m, s in found.items()} }"
            )
    return found


def _block_for(result: dict, method_key: str, split: str) -> dict:
    if method_key.endswith("_excl_filter_only"):
        base = method_key[: -len("_excl_filter_only")]
        return result["excl_filter_only"][base][split]
    if method_key == "model":
        return result[split]
    return result[method_key][split]


def test_train_and_holdout_metrics_match_readme():
    readme = metrics_from_readme()
    result = run(k=5)

    for split in ("train", "holdout"):
        for readme_key, result_key, label in (
            ("r_precision", "mean_r_precision", "R-Precision"),
            ("ndcg_at_5", "mean_ndcg_at_k", "nDCG@5"),
        ):
            expected = readme["model"][split][readme_key]
            got = round(_block_for(result, "model", split)[result_key], 3)
            assert got == expected, (
                f"model {split} {label}: evaluate()={got:.3f} but README.md={expected:.3f}. "
                f"Update README.md if the model changed; fix evaluate()/labels if README is right."
            )


def test_baseline_and_ablation_metrics_match_readme():
    """Pin popularity, random, content-only, and excl. filter-only aggregates."""
    readme = metrics_from_readme()
    result = run(k=5)

    methods = [
        "model",
        "model_excl_filter_only",
        "popularity",
        "popularity_excl_filter_only",
        "random",
        "random_excl_filter_only",
        "content_only",
        "content_only_excl_filter_only",
    ]
    for method in methods:
        for split in ("train", "holdout", "all"):
            block = _block_for(result, method, split)
            expected_n = readme[method][split]["n"]
            assert block["n"] == expected_n, (
                f"{method} {split} n: evaluate()={block['n']} but README.md={expected_n}"
            )
            for readme_key, result_key, label in (
                ("r_precision", "mean_r_precision", "R-Precision"),
                ("ndcg_at_5", "mean_ndcg_at_k", "nDCG@5"),
            ):
                expected = readme[method][split][readme_key]
                got = round(block[result_key], 3)
                assert got == expected, (
                    f"{method} {split} {label}: evaluate()={got:.3f} but "
                    f"README.md={expected:.3f}."
                )


def test_filter_only_profiles_are_washington_alpine_and_beginner_family_east():
    result = run(k=5)
    assert result["filter_only_ids"] == [
        "beginner_family_east",
        "washington_alpine",
    ]
