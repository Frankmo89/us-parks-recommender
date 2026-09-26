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
    r"^\|\s*(Train|Holdout)\s*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|",
    re.MULTILINE,
)


def metrics_from_readme(text: str | None = None) -> dict[str, dict[str, float]]:
    """Parse Train/Holdout R-Precision and nDCG@5 from README's Metrics table."""
    raw = text if text is not None else README_PATH.read_text(encoding="utf-8")
    found: dict[str, dict[str, float]] = {}
    for match in _ROW.finditer(raw):
        split, _n, r_prec, ndcg = match.groups()
        found[split.lower()] = {
            "r_precision": float(r_prec),
            "ndcg_at_5": float(ndcg),
        }
    if "train" not in found or "holdout" not in found:
        raise AssertionError(
            "README.md Metrics table must include Train and Holdout rows "
            f"with R-Precision and nDCG@5; parsed={sorted(found)}"
        )
    return found


def test_train_and_holdout_metrics_match_readme():
    readme = metrics_from_readme()
    result = run(k=5)

    checks = [
        ("train", "r_precision", "mean_r_precision", "R-Precision"),
        ("train", "ndcg_at_5", "mean_ndcg_at_k", "nDCG@5"),
        ("holdout", "r_precision", "mean_r_precision", "R-Precision"),
        ("holdout", "ndcg_at_5", "mean_ndcg_at_k", "nDCG@5"),
    ]
    for split, readme_key, result_key, label in checks:
        expected = readme[split][readme_key]
        got = round(result[split][result_key], 3)
        assert got == expected, (
            f"{split} {label}: evaluate()={got:.3f} but README.md={expected:.3f}. "
            f"Update README.md if the model changed; fix evaluate()/labels if README is right."
        )
