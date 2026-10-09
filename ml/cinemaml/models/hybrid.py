"""Cold start: give movies nobody has rated a place in the collaborative space.

ALS learns a factor vector y_i only for movies with likes. A new release has
none, so collaborative models can never recommend it, while CinemaTime's
catalog is full of them. But every catalog movie has a Sentence-BERT vector
c_i of its overview and tags. On movies with plenty of likes, fit a ridge
regression from content to collaborative factors,

    W = argmin ||C W - Y||^2 + mu ||W||^2 = (C^T C + mu I)^-1 C^T Y,

and give each cold movie y_i = c_i W. Users then score cold movies exactly
like warm ones, with their usual user vector. (Same idea as the "content to
CF" mappings in Gantner et al., ICDM 2010.)
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items
from cinemaml.models.als import ALS


def content_to_factors(content: np.ndarray, factors: np.ndarray, mu: float) -> np.ndarray:
    c = content.astype(np.float64)
    return np.linalg.solve(c.T @ c + mu * np.eye(c.shape[1]), c.T @ factors.astype(np.float64))


class HybridALS:
    def __init__(self, als: ALS, mu: float = 1.0, min_likes: int = 50) -> None:
        self.als = als
        self.mu = mu
        self.min_likes = min_likes
        self.name = f"Hybrid ALS: {als.name} + content map for cold movies (mu={mu:g})"

    def fit(self, fold: Fold, items: Items) -> HybridALS:
        if not hasattr(self.als, "item_factors"):
            self.als.fit(fold, items)
        train_on = fold.item_pop >= self.min_likes
        self.w = content_to_factors(
            items.content[train_on], self.als.item_factors[train_on], self.mu
        )
        self.item_factors = self.als.item_factors.copy()
        cold = fold.is_cold()
        self.item_factors[cold] = (items.content[cold] @ self.w).astype(np.float32)
        return self

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        return self.als.user_factors[users] @ self.item_factors.T
