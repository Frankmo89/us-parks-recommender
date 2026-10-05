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
    r"^\|\s*(Model|Popularity|Random)\s*\|\s*(Train|Holdout|All)\s*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|",
    re.MULTILINE,
)

METHOD_KEYS = {
    "model": None,  # top-level train/holdout/all
    "popularity": "popularity",
    "random": "random",
}


def metrics_from_readme(text: str | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Parse Method × Split R-Precision and nDCG@5 from README's Metrics table."""
    raw = text if text is not None else README_PATH.read_text(encoding="utf-8")
    found: dict[str, dict[str, dict[str, float]]] = {}
    for match in _ROW.finditer(raw):
        method, split, _n, r_prec, ndcg = match.groups()
        method_key = method.lower()
        split_key = split.lower()
        found.setdefault(method_key, {})[split_key] = {
            "r_precision": float(r_prec),
            "ndcg_at_5": float(ndcg),
        }
    required = {
        "model": {"train", "holdout"},
        "popularity": {"train", "holdout", "all"},
        "random": {"train", "holdout", "all"},
    }
    for method, splits in required.items():
        if method not in found or not splits.issubset(found[method]):
            raise AssertionError(
                "README.md Metrics table must include Model/Popularity/Random "
                f"rows for the required splits; parsed={ {m: sorted(s) for m, s in found.items()} }"
            )
    return found


def _block_for(result: dict, method: str, split: str) -> dict:
    key = METHOD_KEYS[method]
    root = result if key is None else result[key]
    return root[split]


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


def test_baseline_metrics_match_readme():
    """Pin popularity and random baselines (same hard filters as the model)."""
    readme = metrics_from_readme()
    result = run(k=5)

    checks = []
    for method in ("popularity", "random"):
        for split in ("train", "holdout", "all"):
            checks.append((method, split, "r_precision", "mean_r_precision", "R-Precision"))
            checks.append((method, split, "ndcg_at_5", "mean_ndcg_at_k", "nDCG@5"))

    for method, split, readme_key, result_key, label in checks:
        expected = readme[method][split][readme_key]
        got = round(_block_for(result, method, split)[result_key], 3)
        assert got == expected, (
            f"{method} {split} {label}: evaluate()={got:.3f} but README.md={expected:.3f}. "
            f"Update README.md if baselines changed; fix evaluate() if README is right."
        )
