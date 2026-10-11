"""Group recommendation on real users instead of synthetic vectors.

CinemaTime's Group Watch scores each candidate for every member and combines
them as 0.8 * min + 0.2 * mean ("soft least misery"). Here random groups of
real test users get one shared top-10 list, and each strategy is judged by
what members actually liked in the following year:

* member recall@10: share of a member's later likes in the group list,
* members served: share of members with at least one liked movie in it,
* worst member: recall of the least-served member, the fairness view.

Member scores are first turned into within-member rank percentiles so one
enthusiastic member cannot dominate through score scale.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cinemaml.experiments.common import best_params, fold, items, write_report
from cinemaml.metrics import top_k
from cinemaml.models import EASE, Content

STRATEGIES = {
    "average (Borda)": lambda p: p.mean(axis=0),
    "least misery (min)": lambda p: p.min(axis=0),
    "CinemaTime: 0.8 min + 0.2 mean": lambda p: 0.8 * p.min(axis=0) + 0.2 * p.mean(axis=0),
    "most pleasure (max)": lambda p: p.max(axis=0),
}


def percentiles(scores: np.ndarray) -> np.ndarray:
    return scores.argsort(axis=1).argsort(axis=1) / (scores.shape[1] - 1)


def run(groups_per_size: int = 600) -> str:
    best, it, test = best_params(), items(), fold("test")
    rng = np.random.default_rng(0)
    models = {
        "EASE": EASE(**best["ease"]).fit(test, it),
        "content (SBERT)": Content().fit(test, it),
    }
    rows = []
    for size in (2, 3, 5):
        picks = [rng.choice(len(test.users), size, replace=False) for _ in range(groups_per_size)]
        for model_name, model in models.items():
            for strategy, combine in STRATEGIES.items():
                member_recall, served, worst = [], [], []
                for g in picks:
                    users = test.users[g]
                    h = test.train[users]
                    p = percentiles(np.asarray(model.score(h, users), dtype=np.float64))
                    combined = combine(p)
                    combined[np.unique(h.indices)] = -np.inf  # nobody wants a rewatch suggestion
                    combined[test.unavailable()] = -np.inf
                    rec = top_k(combined[None, :], 10)[0]
                    r = [np.isin(test.truth[i], rec).sum() / len(test.truth[i]) for i in g]
                    member_recall.append(np.mean(r))
                    served.append(np.mean([x > 0 for x in r]))
                    worst.append(min(r))
                rows.append({"group size": size, "member scores": model_name, "strategy": strategy,
                             "member recall@10": np.mean(member_recall),
                             "members served": np.mean(served), "worst member recall@10": np.mean(worst)})  # fmt: skip
    table = pd.DataFrame(rows)
    text = "\n".join(
        [
            "# Group recommendation strategies on real users (test fold)",
            "",
            f"{groups_per_size} random groups per size, drawn from the {len(test.users):,} test users; "
            "one shared top-10 list per group.",
            "",
            table.to_markdown(index=False, floatfmt=".4f"),
            "",
        ]
    )
    write_report("groups", text)
    return text
