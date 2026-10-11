"""MMR re-ranking: how much accuracy does diversity cost?

CinemaTime re-ranks with Maximal Marginal Relevance,

    next = argmax_i (1 - lambda) * relevance(i) - lambda * max_j in chosen sim(i, j),

with Sentence-BERT cosine as sim and lambda = 0.5 by default. This sweeps
lambda on the test fold, starting from the best single model's top 200, and
measures what users actually liked (NDCG, recall) against intra-list
diversity and catalog coverage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cinemaml.experiments.common import best_params, fold, items, write_report
from cinemaml.metrics import beyond_accuracy, bootstrap, top_k, user_metrics
from cinemaml.models import EASE

LAMBDAS = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7)


def mmr(
    cands: np.ndarray, rel: np.ndarray, content: np.ndarray, lam: float, k: int = 10
) -> np.ndarray:
    """Greedy MMR over one user's candidates (rel min-max normalized to [0, 1])."""
    rel = (rel - rel.min()) / (rel.max() - rel.min() + 1e-12)
    sims = content[cands] @ content[cands].T
    chosen = [int(np.argmax(rel))]
    max_sim = sims[chosen[0]].copy()
    for _ in range(k - 1):
        gain = (1 - lam) * rel - lam * max_sim
        gain[chosen] = -np.inf
        nxt = int(np.argmax(gain))
        chosen.append(nxt)
        max_sim = np.maximum(max_sim, sims[nxt])
    return cands[chosen]


def run() -> str:
    best, it, test = best_params(), items(), fold("test")
    model = EASE(**best["ease"]).fit(test, it)
    pools, rels = [], []
    for s in range(0, len(test.users), 1024):
        u = test.users[s : s + 1024]
        h = test.train[u]
        sc = np.array(model.score(h, u), dtype=np.float32)
        r, c = h.nonzero()
        sc[r, c] = -np.inf
        sc[:, test.unavailable()] = -np.inf
        top = top_k(sc, 200)
        pools.append(top)
        rels.append(np.take_along_axis(sc, top, axis=1))
    pools, rels = np.vstack(pools), np.vstack(rels)

    n_users = int((np.diff(test.train.indptr) > 0).sum())
    rows = []
    for lam in LAMBDAS:
        recs = np.vstack([mmr(p, r, it.content, lam) for p, r in zip(pools, rels, strict=True)])
        per = {"ndcg@10": [], "recall@10": []}
        for rec, t in zip(recs, test.truth, strict=True):
            recall, ndcg, _ = user_metrics(rec, t, 10)
            per["ndcg@10"].append(ndcg)
            per["recall@10"].append(recall)
        ci = bootstrap({k: np.array(v) for k, v in per.items()})
        b = beyond_accuracy(recs, test.item_pop, n_users, it.content)
        rows.append(
            {"lambda": lam + 0.0}
            | {k: f"{v[0]:.4f} ({v[1]:.4f}-{v[2]:.4f})" for k, v in ci.items()}
            | {"diversity@10": f"{b['diversity_ild']:.3f}", "coverage@10": f"{b['coverage']:.3f}",
               "novelty (bits)": f"{b['novelty_bits']:.2f}"}
        )  # fmt: skip
    text = "\n".join(
        [
            "# Diversity vs accuracy: MMR lambda sweep (test fold)",
            "",
            f"Base ranking: {model.name}, top 200 per user; similarity: SBERT cosine. "
            "lambda = 0 is the plain ranking; CinemaTime's item page uses lambda = 0.5.",
            "",
            pd.DataFrame(rows).to_markdown(index=False),
            "",
        ]
    )
    write_report("diversity", text)
    return text
