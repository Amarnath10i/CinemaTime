"""EASE: Embarrassingly Shallow Autoencoder (Steck, WWW 2019).

A linear item-to-item model B that reconstructs each user's likes from their
other likes:

    minimize ||X - X B||^2 + lambda ||B||^2   subject to diag(B) = 0

The zero diagonal stops the trivial solution B = I. It has a closed form:
with P = (X^T X + lambda I)^-1,

    B_ij = -P_ij / P_jj   (i != j),   B_jj = 0

One matrix inverse and no iterations; on MovieLens it routinely beats deep
models. Equivalently, column j of B is a ridge regression of item j on all
other items, which is how the tests check it.

The dense B is n_items^2 floats, too big to serve on a small function host,
so `sparsify()` keeps each item's strongest k weights; the experiments
measure what that costs in accuracy.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items
from cinemaml.models.itemknn import gram, sparsify


def ease_weights(g: np.ndarray, lam: float) -> np.ndarray:
    p = np.linalg.inv(g + lam * np.eye(len(g)))
    b = -p / np.diag(p)[None, :]
    np.fill_diagonal(b, 0.0)
    return b


class EASE:
    def __init__(self, lam: float = 500.0, keep: int | None = None) -> None:
        self.lam = lam
        self.keep = keep
        self.name = f"EASE (lambda={lam:g})" + (f", top {keep} weights per item" if keep else "")

    def fit(self, fold: Fold, items: Items) -> EASE:
        b = ease_weights(gram(fold.train), self.lam).astype(np.float32)
        self.b = b if self.keep is None else signed_sparsify(b, self.keep)
        return self

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        out = history @ self.b
        return out.toarray() if sp.issparse(out) else np.asarray(out)


def signed_sparsify(b: np.ndarray, k: int) -> sp.csr_matrix:
    """EASE weights can be negative ("liking X makes Y less likely"); keep the
    k largest by magnitude per column, preserving sign."""
    mag = sparsify(np.abs(b), k)
    rows, cols = mag.nonzero()
    return sp.csr_matrix((b[rows, cols], (rows, cols)), shape=b.shape)
