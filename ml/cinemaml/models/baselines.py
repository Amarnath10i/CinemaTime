"""Two baselines every model has to beat.

* `Popularity` - the most-liked movies, overall or over the last year. Shows
  how much of a model's score is just "people like popular things".
* `Content` - what CinemaTime does today: Sentence-BERT embeddings of each
  title's overview and tags. A user is the normalized mean of the movies they
  liked; every movie is scored by cosine similarity to that profile. It needs
  no interaction data, so it is also the natural cold-start fallback.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items


class Popularity:
    def __init__(self, recent: bool = False) -> None:
        self.recent = recent
        self.name = "Popularity (last 12 months)" if recent else "Popularity (all time)"

    def fit(self, fold: Fold, items: Items) -> Popularity:
        self.pop = (fold.recent_pop if self.recent else fold.item_pop).astype(np.float32)
        return self

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        return np.broadcast_to(self.pop, (history.shape[0], len(self.pop)))


class Content:
    name = "Content: SBERT profile (current CinemaTime)"

    def fit(self, fold: Fold, items: Items) -> Content:
        self.vectors = items.content
        return self

    def profile(self, history: sp.csr_matrix) -> np.ndarray:
        p = history @ self.vectors
        return p / (np.linalg.norm(p, axis=1, keepdims=True) + 1e-12)

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        return self.profile(history) @ self.vectors.T
