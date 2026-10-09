"""Top-K ranking metrics over the full catalog, plus beyond-accuracy measures.

Every model ranks *all* catalog movies for every user. No sampled negatives:
metrics computed against 100 random negatives can reverse the order of
models (Krichene & Rendle, "On Sampled Metrics for Item Recommendation",
KDD 2020), so they are not used here.

Per user u with held-out likes T_u and top-K list R_u:

    Recall@K = |R_u ∩ T_u| / |T_u|
    NDCG@K   = sum over hits at rank r of 1/log2(r+2), divided by the best
               achievable value for min(K, |T_u|) hits
    Hit@K    = 1 if R_u ∩ T_u is non-empty

Users are independent units, so confidence intervals come from a bootstrap
over users, and model comparisons from a *paired* bootstrap (same users).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def top_k(scores: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k highest scores per row, best first (ties broken by index)."""
    k = min(k, scores.shape[1])
    part = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    rows = np.arange(scores.shape[0])[:, None]
    order = np.lexsort((part, -scores[rows, part]), axis=1)
    return part[rows, order]


_DISCOUNT = 1.0 / np.log2(np.arange(2, 1002))


def user_metrics(rec: np.ndarray, truth: np.ndarray, k: int) -> tuple[float, float, float]:
    """(recall, ndcg, hit) for one user's ranked list."""
    hits = np.isin(rec[:k], truth)
    n_hit = hits.sum()
    recall = n_hit / len(truth)
    dcg = _DISCOUNT[:k][hits].sum()
    idcg = _DISCOUNT[: min(k, len(truth))].sum()
    return float(recall), float(dcg / idcg), float(n_hit > 0)


@dataclass
class Result:
    name: str
    ks: tuple[int, ...]
    per_user: dict[str, np.ndarray]  # e.g. "recall@10" -> (n_users,)
    beyond: dict[str, float] = field(default_factory=dict)
    cold_recall: dict[int, np.ndarray] = field(default_factory=dict)  # users with cold truth only

    def means(self) -> dict[str, float]:
        out = {m: float(v.mean()) for m, v in self.per_user.items()}
        for k, v in self.cold_recall.items():
            out[f"cold_recall@{k}"] = float(v.mean()) if len(v) else float("nan")
        return out | self.beyond


def bootstrap(
    values: dict[str, np.ndarray], n_boot: int = 500, seed: int = 0
) -> dict[str, tuple[float, float, float]]:
    """Mean with a 95% percentile interval, resampling users."""
    rng = np.random.default_rng(seed)
    n = len(next(iter(values.values())))
    idx = rng.integers(0, n, (n_boot, n))
    out = {}
    for name, v in values.items():
        draws = v[idx].mean(axis=1)
        lo, hi = np.quantile(draws, [0.025, 0.975])
        out[name] = (float(v.mean()), float(lo), float(hi))
    return out


def paired_difference(
    a: np.ndarray, b: np.ndarray, n_boot: int = 500, seed: int = 0
) -> tuple[float, float, float]:
    """Mean of b - a over the same users, with a 95% interval."""
    d = b - a
    rng = np.random.default_rng(seed)
    draws = d[rng.integers(0, len(d), (n_boot, len(d)))].mean(axis=1)
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return float(d.mean()), float(lo), float(hi)


def beyond_accuracy(
    recs: np.ndarray, item_pop: np.ndarray, n_train_users: int, content: np.ndarray
) -> dict[str, float]:
    """Coverage, novelty, intra-list diversity and popularity bias of top-K lists.

    recs: (n_users, K) recommended item indices.
    """
    n_items = len(item_pop)
    coverage = len(np.unique(recs)) / n_items
    p = (item_pop[recs] + 1) / (n_train_users + 1)
    novelty = float(np.mean(-np.log2(p)))  # self-information, in bits
    v = content[recs]  # (n_users, K, d), rows L2-normalized
    sims = np.einsum("ukd,ujd->ukj", v, v)
    k = recs.shape[1]
    ild = float(np.mean(1 - (sims.sum(axis=(1, 2)) - k) / (k * (k - 1))))
    pop_rank = item_pop.argsort().argsort() / (n_items - 1)  # 0 = least popular, 1 = most
    return {
        "coverage": coverage,
        "novelty_bits": novelty,
        "diversity_ild": ild,
        "popularity_pct": float(pop_rank[recs].mean()),
    }
