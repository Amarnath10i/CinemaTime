"""Which ranker features matter? Retrain without each group and measure.

Split-gain importance says how often the trees used a feature, not what the
model loses without it: correlated features share credit, and a feature can
be used a lot for little gain in NDCG. So each group below is removed (set to
a constant, which LightGBM can never split on), the ranker is retrained on
the validation fold, and the test-fold NDCG@20 is compared with the full
model on the same users. Candidates are built once per fold and reused, so
only the LightGBM fits are repeated.
"""

from __future__ import annotations

import logging
from dataclasses import replace

import numpy as np
import pandas as pd

from cinemaml.experiments.common import (
    best_params,
    fold,
    items,
    retrievers,
    trained_ranker,
    write_report,
)
from cinemaml.metrics import paired_difference, user_metrics
from cinemaml.models.ranker import FEATURES, Candidates, TwoStage, labels_for, used_trees

log = logging.getLogger(__name__)

GROUPS = {
    "EASE score and rank": ["ease_rel", "ease_rank"],
    "ALS score and rank": ["als_rel", "als_rank"],
    "content score and rank": ["content_score", "content_rank"],
    "popularity and freshness": ["log_likes", "log_likes_last_year", "share_last_year", "is_cold", "age_years"],
    "user-movie fit (genre overlap, era gap)": ["genre_overlap", "year_gap"],
    "user history length": ["user_log_likes"],
}  # fmt: skip


def without(cand: Candidates, columns: list[str]) -> Candidates:
    x = cand.features.copy()
    x[:, [FEATURES.index(c) for c in columns]] = 0.0
    return replace(cand, features=x)


def ndcg_per_user(booster, cand: Candidates, f) -> np.ndarray:
    """NDCG@20 of each test user's re-ranked candidates (truth outside the
    candidates counts as missed, as it would in production)."""
    s = booster.predict(cand.features, num_iteration=used_trees(booster))
    starts = np.concatenate([[0], np.cumsum(cand.groups)])
    out = np.empty(len(f.users))
    for i, truth in enumerate(f.truth):
        lo, hi = starts[i], starts[i + 1]
        top = cand.items[lo:hi][np.argsort(-s[lo:hi], kind="stable")[:20]]
        out[i] = user_metrics(top, truth, 20)[1]
    return out


def run() -> str:
    best, it = best_params(), items()
    valid, test = fold("valid"), fold("test")

    base = trained_ranker("valid", best)
    train_cand = base.candidates(valid.users)
    labels = labels_for(train_cand, valid)

    scorer = TwoStage(retrievers(test, it, best), base.per_source).set_fold(test, it)
    test_cand = scorer.candidates(test.users)
    full = ndcg_per_user(base.booster, test_cand, test)

    rows = [
        {
            "removed": "nothing (full ranker)",
            "ndcg@20": f"{full.mean():.4f}",
            "change": "-",
            "relative": "-",
        }
    ]
    for name, columns in GROUPS.items():
        booster = base.train(without(train_cand, columns), labels)
        ablated = ndcg_per_user(booster, without(test_cand, columns), test)
        d, lo, hi = paired_difference(full, ablated)
        rows.append({"removed": name, "ndcg@20": f"{ablated.mean():.4f}",
                     "change": f"{d:+.4f} ({lo:+.4f} to {hi:+.4f})", "relative": f"{d / full.mean():+.1%}"})  # fmt: skip
        log.info("without %s: %.4f (%+.4f)", name, ablated.mean(), d)

    text = "\n".join(
        [
            "# Ranker feature ablation (test fold)",
            "",
            "Each feature group is removed, the LambdaRank model is retrained on the validation "
            "fold's candidates, and test NDCG@20 is compared with the full ranker on the same "
            f"{len(test.users):,} users (paired bootstrap, 95% interval). A negative change means "
            "the group helps.",
            "",
            pd.DataFrame(rows).to_markdown(index=False),
            "",
        ]
    )
    write_report("ablation", text)
    return text
