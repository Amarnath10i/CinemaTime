"""Personalized recommendations for a visitor, from the movies they liked.

The same two stages as offline (ml/cinemaml/models/ranker.py), with every
model reduced to arrays exported by `cinemaml export`:

* EASE        scores = h @ B, with B kept to each movie's strongest weights
* ALS         a visitor has no trained user vector, so theirs is solved in
              closed form from their likes ("fold-in") against item factors
              in which new releases were placed by the content-to-ALS map
* content     cosine to the mean Sentence-BERT vector of their likes
* popularity  likes over the last year of interaction data

then the shared ranker features (features.py) and the LightGBM LambdaRank
model, evaluated by trees.py. EASE is linear, so each EASE score is an exact
sum of one contribution per liked movie; the largest one is the honest answer
to "why was this recommended?".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from recsys import features
from recsys.features import ItemContext
from recsys.trees import TreeEnsemble

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
_EPOCH = date(1970, 1, 1)


@dataclass
class Rec:
    item: int  # item index into Engine.catalog_ids
    score: float  # ranker output; only the order matters
    because: int | None  # liked item with the largest EASE contribution, if positive
    similar: int | None  # liked item closest in content
    cold: bool  # nobody had liked it in the interaction data (e.g. a new release)


class Engine:
    def __init__(self, meta: dict, arrays: dict[str, np.ndarray], content: np.ndarray) -> None:
        if meta["features"] != features.FEATURES:
            raise ValueError("artifacts were trained with different ranker features; re-export")
        self.meta = meta
        self.catalog_ids = [str(c) for c in arrays["catalog_ids"]]
        self.position = {cid: i for i, cid in enumerate(self.catalog_ids)}
        self.n_items = len(self.catalog_ids)
        self.ctx = ItemContext(
            genres=arrays["genres"].astype(np.float32),
            year=arrays["year"].astype(np.float64),
            reference_year=int(meta["reference_year"]),
            item_pop=arrays["item_pop"].astype(np.float64),
            recent_pop=arrays["recent_pop"].astype(np.float64),
        )
        self.released_day = arrays["released_day"]
        self.ease_indptr = arrays["ease_indptr"]
        self.ease_indices = arrays["ease_indices"]
        self.ease_data = arrays["ease_data"]
        self.factors = arrays["als_factors"]
        self.gram = arrays["als_gram"]  # Y^T Y + lambda I over the trained item factors
        self.alpha = float(meta["als"]["alpha"])
        self.popularity = arrays["recent_pop"].astype(np.float32)
        self.content = np.asarray(content, dtype=np.float32)
        self.ranker = TreeEnsemble.from_arrays(arrays, meta["features"])
        self.per_source = meta["per_source"]

    @classmethod
    def load(cls, content: np.ndarray, directory: Path = ARTIFACTS) -> Engine:
        """`content`: (n_items, d) L2-normalized vectors in the order of
        `catalog_ids(directory)`; the API reads them from its FAISS index."""
        meta = json.loads((Path(directory) / "meta.json").read_text(encoding="utf-8"))
        with np.load(Path(directory) / "model.npz", allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        return cls(meta, arrays, content)

    @staticmethod
    def catalog_ids_in(directory: Path = ARTIFACTS) -> list[str]:
        with np.load(Path(directory) / "model.npz", allow_pickle=False) as z:
            return [str(c) for c in z["catalog_ids"]]

    # stage 1 ---------------------------------------------------------------

    def available(self, today: date | None = None) -> np.ndarray:
        """Movies already released (an unknown date counts as released)."""
        day = ((today or date.today()) - _EPOCH).days
        return self.released_day <= day

    def ease_scores(self, liked: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
        """sum over liked i of w_i * B[i, :], straight from the CSR arrays."""
        starts, ends = self.ease_indptr[liked], self.ease_indptr[liked + 1]
        lens = ends - starts
        take = np.repeat(starts - np.cumsum(lens) + lens, lens) + np.arange(lens.sum())
        vals = self.ease_data[take].astype(np.float64)
        if weights is not None:
            vals *= np.repeat(weights, lens)
        return np.bincount(self.ease_indices[take], weights=vals, minlength=self.n_items)

    def als_user(self, liked: np.ndarray) -> np.ndarray:
        """Exact ALS user vector given the item factors (Hu et al.'s normal equations)."""
        ys = self.factors[liked].astype(np.float64)
        a = self.gram + self.alpha * ys.T @ ys
        return np.linalg.solve(a, (1 + self.alpha) * ys.sum(axis=0))

    def retrieve(
        self,
        liked: list[np.ndarray],
        weights: list[np.ndarray] | None = None,
        excluded: np.ndarray | None = None,
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Binary history and every retriever's scores for a batch of users.

        weights: optional recency weight per like for EASE (offline replays
        pass the same decayed weights the model was evaluated with; a live
        visitor's likes are all recent, weight 1). excluded: movies nobody
        may be shown, e.g. ones not released yet.
        """
        n = len(liked)
        history = np.zeros((n, self.n_items), dtype=np.float32)
        scores = {name: np.empty((n, self.n_items), dtype=np.float32) for name in features.RETRIEVERS}
        for u, items in enumerate(liked):
            history[u, items] = 1.0
            w = None if weights is None else weights[u]
            scores["ease"][u] = self.ease_scores(items, w)
            scores["als"][u] = self.factors @ self.als_user(items).astype(np.float32)
        profile = history @ self.content
        profile /= np.linalg.norm(profile, axis=1, keepdims=True) + 1e-12
        scores["content"][:] = profile @ self.content.T
        scores["popularity"][:] = self.popularity
        blocked = history > 0
        if excluded is not None:
            blocked |= excluded[None, :]
        for s in scores.values():
            s[blocked] = -np.inf
        return history, scores

    # stage 2 ---------------------------------------------------------------

    def rank(
        self,
        liked: list[np.ndarray],
        weights: list[np.ndarray] | None = None,
        excluded: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Candidates and ranker scores: (user row, item, score, features)."""
        history, scores = self.retrieve(liked, weights, excluded)
        pick = features.pick_candidates(scores, self.per_source)
        r, c, x = features.build(self.ctx, history, scores, pick)
        return r, c, self.ranker.predict(x), x

    def top(
        self,
        liked: list[np.ndarray],
        k: int,
        weights: list[np.ndarray] | None = None,
        excluded: np.ndarray | None = None,
    ) -> np.ndarray:
        """(n_users, k) best items per user (-1 pads users with fewer candidates)."""
        r, c, s, _ = self.rank(liked, weights, excluded)
        out = np.full((len(liked), k), -1, dtype=np.int64)
        order = np.lexsort((-s, r))  # by user, then best first
        r, c = r[order], c[order]
        starts = np.searchsorted(r, np.arange(len(liked)))
        pos = np.arange(len(r)) - starts[r]
        keep = pos < k
        out[r[keep], pos[keep]] = c[keep]
        return out

    def recommend(self, liked_ids: list[str], n: int = 20, today: date | None = None) -> list[Rec]:
        """Top-n for one visitor. Ids outside the trained catalog are ignored;
        with no usable likes the answer is last year's most liked movies."""
        liked = np.array(sorted({self.position[i] for i in liked_ids if i in self.position}),
                         dtype=np.int64)  # fmt: skip
        excluded = ~self.available(today)
        if len(liked) == 0:
            pop = np.where(excluded, -np.inf, self.popularity)
            best = features.top_k(pop[None, :], n)[0]
            return [Rec(int(i), float(pop[i]), None, None, bool(self.ctx.cold[i])) for i in best]

        r, c, s, _ = self.rank([liked], excluded=excluded)
        order = np.argsort(-s, kind="stable")[:n]
        items = c[order]
        # explanations: per-liked-movie EASE contributions and content similarity
        contrib = np.zeros((len(liked), len(items)))
        for row, i in enumerate(liked):
            lo, hi = self.ease_indptr[i], self.ease_indptr[i + 1]
            cols = self.ease_indices[lo:hi]
            pos = np.minimum(np.searchsorted(cols, items), max(len(cols) - 1, 0))
            hit = (cols[pos] == items) if len(cols) else np.zeros(len(items), dtype=bool)
            contrib[row, hit] = self.ease_data[lo:hi][pos[hit]]
        sims = self.content[liked] @ self.content[items].T
        out = []
        for col, (item, score) in enumerate(zip(items, s[order], strict=True)):
            best = int(np.argmax(contrib[:, col]))
            out.append(
                Rec(
                    int(item),
                    float(score),
                    int(liked[best]) if contrib[best, col] > 0 else None,
                    int(liked[int(np.argmax(sims[:, col]))]),
                    bool(self.ctx.cold[item]),
                )
            )
        return out
