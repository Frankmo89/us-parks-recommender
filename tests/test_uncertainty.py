"""Bootstrap ranges and paired tests (src/uncertainty.py, src/evaluate.py)."""

from __future__ import annotations

import pytest

from src import evaluate, uncertainty


def test_constant_scores_have_a_zero_width_range():
    assert uncertainty.bootstrap_ci([0.5] * 10) == pytest.approx((0.5, 0.5))


def test_range_contains_the_mean_and_is_deterministic():
    values = [0.0, 0.25, 0.5, 0.5, 0.75, 1.0, 1.0, 0.2]
    low, high = uncertainty.bootstrap_ci(values)
    assert low < sum(values) / len(values) < high
    assert uncertainty.bootstrap_ci(values) == (low, high)


def test_sign_flip_p_value_exact_small_case():
    # Three equal positive gains: only all-plus and all-minus are as extreme -> 2/8.
    assert uncertainty.sign_flip_p_value([0.1, 0.1, 0.1]) == pytest.approx(0.25)
    # Ties carry no evidence.
    assert uncertainty.sign_flip_p_value([0.0, 0.0]) == 1.0
    assert uncertainty.sign_flip_p_value([0.1, 0.1, 0.1, 0.0]) == pytest.approx(0.25)


def test_paired_test_counts_and_direction():
    result = uncertainty.paired_test([1.0, 0.5, 0.2, 0.3], [0.5, 0.5, 0.4, 0.1])
    assert (result["wins"], result["ties"], result["losses"]) == (2, 1, 1)
    assert result["mean_diff"] == pytest.approx(0.125)
    assert result["ci_low"] <= result["mean_diff"] <= result["ci_high"]
    with pytest.raises(ValueError):
        uncertainty.paired_test([1.0], [1.0, 0.0])


@pytest.fixture(scope="module")
def result():
    return evaluate.run(k=5)


def test_evaluate_reports_ranges_around_the_published_means(result):
    for scope in ("all", "all_excl_filter_only"):
        report = result["uncertainty"][scope]
        for method, summary in report["summary"].items():
            for metric in ("r_precision", "ndcg_at_k"):
                s = summary[metric]
                assert s["ci_low"] <= s["mean"] <= s["ci_high"], (scope, method, metric)
    model = result["uncertainty"]["all"]["summary"]["model"]
    assert model["r_precision"]["mean"] == pytest.approx(result["all"]["mean_r_precision"])
    assert model["ndcg_at_k"]["mean"] == pytest.approx(result["all"]["mean_ndcg_at_k"])


def test_paired_diffs_match_the_means(result):
    report = result["uncertainty"]["all"]
    for baseline in evaluate.BASELINES:
        diff = report["model_vs"][baseline]["ndcg_at_k"]["mean_diff"]
        expected = result["all"]["mean_ndcg_at_k"] - result[baseline]["all"]["mean_ndcg_at_k"]
        assert diff == pytest.approx(expected)


def test_readme_uncertainty_table_matches_evaluate(result):
    import re
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| Model vs (Content-only|Popularity|Random) \| (R-Precision|nDCG@5) \| ([+−-][0-9.]+) \|"
        r" ([+−-][0-9.]+) to ([+−-][0-9.]+) \| (<?[0-9.]+) \| (\d+)/(\d+)/(\d+) \|$",
        text,
        re.MULTILINE,
    )
    assert len(rows) == 6
    baseline_key = {"Content-only": "content_only", "Popularity": "popularity", "Random": "random"}
    metric_key = {"R-Precision": "r_precision", "nDCG@5": "ndcg_at_k"}

    def num(raw: str) -> float:
        return float(raw.replace("−", "-"))

    for baseline, metric, diff, low, high, p, wins, ties, losses in rows:
        t = result["uncertainty"]["all"]["model_vs"][baseline_key[baseline]][metric_key[metric]]
        assert num(diff) == round(t["mean_diff"], 3), (baseline, metric)
        assert (num(low), num(high)) == (round(t["ci_low"], 3), round(t["ci_high"], 3)), (baseline, metric)
        if p == "<0.001":
            assert t["p_value"] < 0.001
        else:
            assert float(p) == round(t["p_value"], 3)
        assert (int(wins), int(ties), int(losses)) == (t["wins"], t["ties"], t["losses"])
