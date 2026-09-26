"""Pin train/holdout metrics to the values published in README.md.

Fails if the model or eval labels change without updating the README.
"""

from src.evaluate import run

# README.md Metrics table (3 decimal places).
README_TRAIN_R_PRECISION = 0.729
README_TRAIN_NDCG_AT_5 = 0.765
README_HOLDOUT_R_PRECISION = 0.794
README_HOLDOUT_NDCG_AT_5 = 0.808


def test_train_and_holdout_metrics_match_readme():
    result = run(k=5)
    train = result["train"]
    holdout = result["holdout"]

    assert round(train["mean_r_precision"], 3) == README_TRAIN_R_PRECISION
    assert round(train["mean_ndcg_at_k"], 3) == README_TRAIN_NDCG_AT_5
    assert round(holdout["mean_r_precision"], 3) == README_HOLDOUT_R_PRECISION
    assert round(holdout["mean_ndcg_at_k"], 3) == README_HOLDOUT_NDCG_AT_5
