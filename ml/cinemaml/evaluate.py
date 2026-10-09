"""Run any recommender over a fold: rank the whole catalog for every user."""

from __future__ import annotations

import logging
import time
from typing import Protocol

import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items
from cinemaml.metrics import Result, beyond_accuracy, top_k, user_metrics

log = logging.getLogger(__name__)


class Recommender(Protocol):
    name: str

    def fit(self, fold: Fold, items: Items) -> Recommender: ...

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        """(len(users), n_items) scores; higher is better. `history` holds the
        users' training likes (rows of fold.train)."""
        ...


def recommend(
    model: Recommender, fold: Fold, users: np.ndarray, k: int, batch: int = 1024
) -> np.ndarray:
    """Top-k items per user, never including what they already liked."""
    out = np.empty((len(users), k), dtype=np.int32)
    for s in range(0, len(users), batch):
        u = users[s : s + batch]
        h = fold.train[u]
        scores = np.array(model.score(h, u), dtype=np.float32)  # own copy: we mask it below
        rows, cols = h.nonzero()
        scores[rows, cols] = -np.inf
        out[s : s + len(u)] = top_k(scores, k)
    return out


def evaluate(model: Recommender, fold: Fold, items: Items, ks=(10, 20, 50)) -> Result:
    t0 = time.perf_counter()
    k_max = max(ks)
    recs = recommend(model, fold, fold.users, k_max)
    per_user = {
        f"{m}@{k}": np.empty(len(fold.users)) for k in ks for m in ("recall", "ndcg", "hit")
    }
    cold = fold.is_cold()
    cold_recall: dict[int, list[float]] = {k: [] for k in ks}
    for i, truth in enumerate(fold.truth):
        for k in ks:
            r, n, h = user_metrics(recs[i], truth, k)
            per_user[f"recall@{k}"][i], per_user[f"ndcg@{k}"][i], per_user[f"hit@{k}"][i] = r, n, h
        cold_truth = truth[cold[truth]]
        if len(cold_truth):
            for k in ks:
                cold_recall[k].append(np.isin(recs[i, :k], cold_truth).sum() / len(cold_truth))
    n_train_users = int((np.diff(fold.train.indptr) > 0).sum())
    beyond = beyond_accuracy(recs[:, :10], fold.item_pop, n_train_users, items.content)
    log.info("%s on %s: %.1fs", model.name, fold.name, time.perf_counter() - t0)
    return Result(
        model.name, tuple(ks), per_user, beyond, {k: np.array(v) for k, v in cold_recall.items()}
    )
