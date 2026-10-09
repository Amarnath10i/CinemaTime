"""Item-based collaborative filtering ("people who liked X also liked Y").

Similarity is cosine over the binary user-item matrix X, with shrinkage so a
pair liked together by 2 users does not look as strong as one liked together
by 2,000:

    sim(i, j) = (X^T X)_ij / (sqrt(n_i * n_j) + shrink)

Only the `neighbors` most similar items per item are kept. A user's score for
item j is the sum of j's similarities to the items they liked.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items


def gram(train: sp.csr_matrix) -> np.ndarray:
    """Item co-occurrence counts X^T X as a dense matrix."""
    return np.asarray((train.T @ train).todense(), dtype=np.float64)


class ItemKNN:
    def __init__(self, neighbors: int = 200, shrink: float = 50.0) -> None:
        self.neighbors = neighbors
        self.shrink = shrink
        self.name = f"Item-kNN (cosine, k={neighbors}, shrink={shrink:g})"

    def fit(self, fold: Fold, items: Items) -> ItemKNN:
        g = gram(fold.train)
        n = np.diag(g).copy()
        sim = g / (np.sqrt(np.outer(n, n)) + self.shrink)
        np.fill_diagonal(sim, 0.0)
        self.sim = sparsify(sim, self.neighbors)
        return self

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        return (history @ self.sim).toarray()


def sparsify(dense: np.ndarray, k: int) -> sp.csr_matrix:
    """Keep the k largest entries of each column (an item's strongest neighbors)."""
    n = dense.shape[0]
    k = min(k, n - 1)
    rows = np.argpartition(-dense, k - 1, axis=0)[:k]  # (k, n): top rows per column
    cols = np.broadcast_to(np.arange(n), rows.shape)
    vals = dense[rows, cols]
    keep = vals > 0
    return sp.csr_matrix(
        (vals[keep].astype(np.float32), (rows[keep], cols[keep])), shape=dense.shape
    )
