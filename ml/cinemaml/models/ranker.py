"""Two-stage recommendation: candidate retrieval, then learned re-ranking.

Stage 1 (retrieval) asks several cheap models for their top candidates:
EASE, hybrid ALS (which can surface cold movies), last-year popularity and
content similarity. Their union is usually a few hundred movies per user.

Stage 2 (ranking) is a LightGBM LambdaRank model that re-orders each user's
candidates using every retriever's score and rank plus signals none of them
models on its own: how new the movie is, whether anyone has rated it yet,
how much its genres overlap with the user's, and how far its release year is
from the eras the user usually likes. LambdaRank optimizes NDCG directly by
weighting pairwise swaps by their effect on the metric.

The ranker is trained on the validation fold (retrievers fitted on data
before the validation cutoff, labels = likes inside the validation window)
and applied unchanged to the test fold with retrievers refitted on the
test cutoff, so no future information leaks into training.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items
from cinemaml.metrics import top_k

log = logging.getLogger(__name__)

FEATURES = [
    "ease_score", "ease_rank", "als_score", "als_rank", "content_score", "content_rank",
    "log_likes", "log_likes_last_year", "share_last_year", "is_cold", "age_years",
    "year_gap", "genre_overlap", "user_log_likes", "user_recent_share",
]  # fmt: skip


def genre_matrix(items: Items) -> np.ndarray:
    genres = items.table["genres"].fillna("").str.split(",")
    names = sorted({g.strip() for gs in genres for g in gs if g.strip()})
    index = {g: i for i, g in enumerate(names)}
    m = np.zeros((len(items), len(names)), dtype=np.float32)
    for row, gs in enumerate(genres):
        for g in gs:
            if g.strip():
                m[row, index[g.strip()]] = 1.0
    return m


def _ranks(scores: np.ndarray) -> np.ndarray:
    """1 = best, per row."""
    order = np.argsort(-scores, axis=1, kind="stable")
    ranks = np.empty_like(order)
    np.put_along_axis(ranks, order, np.arange(1, scores.shape[1] + 1)[None, :], axis=1)
    return ranks


@dataclass
class Candidates:
    users: np.ndarray  # (n_rows,) user id per candidate row
    items: np.ndarray  # (n_rows,) item index
    features: np.ndarray  # (n_rows, len(FEATURES))
    groups: np.ndarray  # candidates per user, in order


class TwoStage:
    def __init__(self, retrievers: dict, per_source: dict[str, int], params: dict | None = None):
        """retrievers: name -> fitted model with .score(history, users); must
        include "ease", "als", "popularity" and "content"."""
        self.retrievers = retrievers
        self.per_source = per_source
        self.params = {
            "objective": "lambdarank", "metric": "ndcg", "ndcg_eval_at": [10, 20],
            "learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 200,
            "feature_fraction": 0.9, "lambdarank_truncation_level": 30, "verbose": -1,
            "seed": 0, "deterministic": True, "force_row_wise": True, "num_threads": 8,
        } | (params or {})  # fmt: skip
        self.name = "Two-stage: EASE + hybrid ALS + popularity + content -> LambdaRank"

    def set_fold(self, fold: Fold, items: Items, retrievers: dict | None = None) -> TwoStage:
        """Point the ranker at a (possibly different) fold and its retrievers."""
        self.fold, self.items = fold, items
        if retrievers is not None:
            self.retrievers = retrievers
        self._genres = genre_matrix(items)
        year = items.table["year"].to_numpy(np.float64)
        self._age = fold.cutoff.year - year
        self._year = year
        self._log_pop = np.log1p(fold.item_pop)
        self._log_recent = np.log1p(fold.recent_pop)
        self._share = fold.recent_pop / (fold.item_pop + 1.0)
        self._cold = fold.is_cold().astype(np.float32)
        return self

    def candidates(self, users: np.ndarray, batch: int = 512) -> Candidates:
        rows_u, rows_i, feats, groups = [], [], [], []
        for s in range(0, len(users), batch):
            u = users[s : s + batch]
            h = self.fold.train[u]
            seen_r, seen_c = h.nonzero()
            scores = {}
            for name in ("ease", "als", "content", "popularity"):
                sc = np.array(self.retrievers[name].score(h, u), dtype=np.float32)
                sc[seen_r, seen_c] = -np.inf
                scores[name] = sc
            ranks = {n: _ranks(scores[n]) for n in ("ease", "als", "content")}
            pick = np.zeros(scores["ease"].shape, dtype=bool)
            for name, n in self.per_source.items():
                np.put_along_axis(pick, top_k(scores[name], n), True, axis=1)
            pick[seen_r, seen_c] = False

            # user-level context from their history
            n_likes = np.diff(h.indptr).astype(np.float64)
            ages = self.fold.age_days[u]
            recent = np.asarray((ages.multiply(ages < 365) > 0).sum(axis=1)).ravel()
            g_dist = np.asarray(h @ self._genres) / np.maximum(n_likes, 1)[:, None]
            liked_years = h.multiply(np.nan_to_num(self._year, nan=0.0)).sum(axis=1)
            known = h @ (~np.isnan(self._year)).astype(np.float32)
            mean_year = np.asarray(liked_years).ravel() / np.maximum(np.asarray(known).ravel(), 1)

            r, c = np.nonzero(pick)
            n_genres = np.maximum(self._genres[c].sum(axis=1), 1)
            f = np.column_stack([
                scores["ease"][r, c], ranks["ease"][r, c],
                scores["als"][r, c], ranks["als"][r, c],
                scores["content"][r, c], ranks["content"][r, c],
                self._log_pop[c], self._log_recent[c], self._share[c], self._cold[c],
                self._age[c], np.abs(self._year[c] - mean_year[r]),
                np.einsum("ng,ng->n", g_dist[r], self._genres[c]) / n_genres,
                np.log1p(n_likes[r]), recent[r] / np.maximum(n_likes[r], 1),
            ]).astype(np.float32)  # fmt: skip
            rows_u.append(u[r])
            rows_i.append(c.astype(np.int32))
            feats.append(f)
            groups.append(np.bincount(r, minlength=len(u)))
        return Candidates(
            np.concatenate(rows_u), np.concatenate(rows_i), np.vstack(feats), np.concatenate(groups)
        )

    def fit(self, fold: Fold, items: Items, valid_share: float = 0.2) -> TwoStage:
        self.set_fold(fold, items)
        cand = self.candidates(fold.users)
        truth = {u: set(t.tolist()) for u, t in zip(fold.users, fold.truth, strict=True)}
        labels = np.fromiter(
            (i in truth[u] for u, i in zip(cand.users, cand.items, strict=True)), dtype=np.float32
        )
        self.candidate_recall = labels.sum() / sum(len(t) for t in fold.truth)
        log.info(
            "candidates: %d rows, recall of all likes %.3f", len(labels), self.candidate_recall
        )

        # hold out whole users for early stopping
        rng = np.random.default_rng(0)
        hold = rng.random(len(fold.users)) < valid_share
        row_hold = np.repeat(hold, cand.groups)
        dtrain = lgb.Dataset(cand.features[~row_hold], labels[~row_hold], group=cand.groups[~hold],
                             feature_name=FEATURES)  # fmt: skip
        dvalid = dtrain.create_valid(
            cand.features[row_hold], labels[row_hold], group=cand.groups[hold]
        )
        self.booster = lgb.train(
            self.params, dtrain, 1000, valid_sets=[dvalid],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )  # fmt: skip
        return self

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        cand = self.candidates(users)
        out = np.full((len(users), self.fold.n_items), -np.inf, dtype=np.float32)
        row = np.repeat(np.arange(len(users)), cand.groups)
        out[row, cand.items] = self.booster.predict(
            cand.features, num_iteration=self.booster.best_iteration
        )
        return out
