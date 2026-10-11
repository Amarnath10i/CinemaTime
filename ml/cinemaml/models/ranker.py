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
import sys
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import scipy.sparse as sp

from cinemaml.config import REPO
from cinemaml.data import Fold, Items

# The feature code lives with the API so training and serving share it.
sys.path.insert(0, str(REPO / "backend"))
from recsys import features  # noqa: E402
from recsys.features import FEATURES, ItemContext  # noqa: E402

log = logging.getLogger(__name__)


def genre_names(items: Items) -> list[str]:
    genres = items.table["genres"].fillna("").str.split(",")
    return sorted({g.strip() for gs in genres for g in gs if g.strip()})


def genre_matrix(items: Items) -> np.ndarray:
    index = {g: i for i, g in enumerate(genre_names(items))}
    m = np.zeros((len(items), len(index)), dtype=np.float32)
    for row, gs in enumerate(items.table["genres"].fillna("").str.split(",")):
        for g in gs:
            if g.strip():
                m[row, index[g.strip()]] = 1.0
    return m


def item_context(fold: Fold, items: Items) -> ItemContext:
    return ItemContext(
        genres=genre_matrix(items),
        year=items.table["year"].to_numpy(np.float64),
        reference_year=fold.cutoff.year,
        item_pop=fold.item_pop.astype(np.float64),
        recent_pop=fold.recent_pop.astype(np.float64),
    )


@dataclass
class Candidates:
    users: np.ndarray  # (n_rows,) user id per candidate row
    items: np.ndarray  # (n_rows,) item index
    features: np.ndarray  # (n_rows, len(FEATURES))
    groups: np.ndarray  # candidates per user, in order


def labels_for(cand: Candidates, fold: Fold) -> np.ndarray:
    """1 for each candidate the user went on to like inside the fold's window."""
    truth = {u: set(t.tolist()) for u, t in zip(fold.users, fold.truth, strict=True)}
    return np.fromiter(
        (i in truth[u] for u, i in zip(cand.users, cand.items, strict=True)), dtype=np.float32
    )


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
        self.ctx = item_context(fold, items)
        return self

    def retrieve(self, history: sp.csr_matrix, users: np.ndarray) -> dict[str, np.ndarray]:
        """Every retriever's scores, -inf where a movie cannot be recommended."""
        seen_r, seen_c = history.nonzero()
        gone = self.fold.unavailable()
        scores = {}
        for name in features.RETRIEVERS:
            sc = np.array(self.retrievers[name].score(history, users), dtype=np.float32)
            sc[seen_r, seen_c] = -np.inf
            sc[:, gone] = -np.inf
            scores[name] = sc
        return scores

    def candidates(self, users: np.ndarray, batch: int = 512) -> Candidates:
        rows_u, rows_i, feats, groups = [], [], [], []
        for s in range(0, len(users), batch):
            u = users[s : s + batch]
            h = self.fold.train[u]
            scores = self.retrieve(h, u)
            pick = features.pick_candidates(scores, self.per_source)
            r, c, f = features.build(self.ctx, h.toarray(), scores, pick)
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
        labels = labels_for(cand, fold)
        self.candidate_recall = labels.sum() / sum(len(t) for t in fold.truth)
        log.info(
            "candidates: %d rows, recall of all likes %.3f", len(labels), self.candidate_recall
        )
        self.booster = self.train(cand, labels, valid_share)
        return self

    def train(self, cand: Candidates, labels: np.ndarray, valid_share: float = 0.2) -> lgb.Booster:
        """LambdaRank on candidate lists, early-stopped on held-out whole users."""
        rng = np.random.default_rng(0)
        hold = rng.random(len(cand.groups)) < valid_share
        row_hold = np.repeat(hold, cand.groups)
        dtrain = lgb.Dataset(cand.features[~row_hold], labels[~row_hold], group=cand.groups[~hold],
                             feature_name=FEATURES)  # fmt: skip
        dvalid = dtrain.create_valid(
            cand.features[row_hold], labels[row_hold], group=cand.groups[hold]
        )
        return lgb.train(
            self.params, dtrain, 1000, valid_sets=[dvalid],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )  # fmt: skip

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        cand = self.candidates(users)
        out = np.full((len(users), self.fold.n_items), -np.inf, dtype=np.float32)
        row = np.repeat(np.arange(len(users)), cand.groups)
        out[row, cand.items] = self.booster.predict(
            cand.features, num_iteration=self.booster.best_iteration
        )
        return out
