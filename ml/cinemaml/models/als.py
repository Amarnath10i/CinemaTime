"""Implicit-feedback matrix factorization: ALS with conjugate gradient.

Hu, Koren & Volinsky, "Collaborative Filtering for Implicit Feedback
Datasets" (ICDM 2008). A like is a preference p_ui = 1 held with confidence
c_ui = 1 + alpha; everything unseen is a weak p_ui = 0 with confidence 1:

    minimize  sum_ui c_ui (p_ui - x_u . y_i)^2 + lambda (sum ||x_u||^2 + sum ||y_i||^2)

With Y fixed, each user's optimum solves a k x k system

    (Y^T Y + alpha * sum_{i in u} y_i y_i^T + lambda I) x_u = (1 + alpha) * sum_{i in u} y_i

and symmetrically for items. Forming that matrix per user costs O(n_u k^2);
following Takacs, Pilaszy & Tikk (RecSys 2011) the system is instead solved
approximately with a few conjugate-gradient steps warm-started from the
previous iterate, which only needs matrix-vector products, O(n_u k) per user.
Here CG runs for all users at once with NumPy and sparse products.

`fold_in` solves the user system exactly for someone not seen in training,
e.g. a visitor who liked a few movies in the browser: no retraining needed.
"""

from __future__ import annotations

import logging

import numpy as np
import scipy.sparse as sp

from cinemaml.data import Fold, Items

log = logging.getLogger(__name__)


def _pair_dots(
    a: np.ndarray, b: np.ndarray, m: sp.csr_matrix, chunk: int = 2_000_000
) -> np.ndarray:
    """a[u] . b[i] for every non-zero (u, i) of m, in chunks to bound memory."""
    rows = np.repeat(np.arange(m.shape[0]), np.diff(m.indptr))
    cols = m.indices
    out = np.empty(m.nnz, dtype=np.float32)
    for s in range(0, m.nnz, chunk):
        e = s + chunk
        out[s:e] = np.einsum("nk,nk->n", a[rows[s:e]], b[cols[s:e]])
    return out


def cg_solve(
    x: np.ndarray, y: np.ndarray, m: sp.csr_matrix, alpha: float, lam: float, steps: int
) -> np.ndarray:
    """Improve every row of x towards the exact ALS solution given the fixed side y.

    A_u v = v (Y^T Y + lam I) + alpha * sum_{i in u} y_i (y_i . v)
    b_u   = (1 + alpha) * sum_{i in u} y_i
    """
    gram = y.T @ y + lam * np.eye(y.shape[1], dtype=np.float32)

    def apply_a(v: np.ndarray) -> np.ndarray:
        w = sp.csr_matrix((alpha * _pair_dots(v, y, m), m.indices, m.indptr), shape=m.shape)
        return v @ gram + w @ y

    b = (1 + alpha) * (m @ y)
    r = b - apply_a(x)
    p = r.copy()
    rs = np.einsum("uk,uk->u", r, r)
    for _ in range(steps):
        ap = apply_a(p)
        step = rs / np.maximum(np.einsum("uk,uk->u", p, ap), 1e-12)
        x = x + step[:, None] * p
        r = r - step[:, None] * ap
        rs_new = np.einsum("uk,uk->u", r, r)
        p = r + (rs_new / np.maximum(rs, 1e-12))[:, None] * p
        rs = rs_new
    return x


class ALS:
    def __init__(
        self,
        factors: int = 64,
        alpha: float = 20.0,
        lam: float = 10.0,
        iterations: int = 12,
        cg_steps: int = 3,
        seed: int = 0,
    ) -> None:
        self.factors = factors
        self.alpha = alpha
        self.lam = lam
        self.iterations = iterations
        self.cg_steps = cg_steps
        self.seed = seed
        self.name = f"ALS (k={factors}, alpha={alpha:g}, lambda={lam:g})"

    def fit(self, fold: Fold, items: Items | None = None) -> ALS:
        r = fold.train.astype(np.float32).tocsr()
        rt = r.T.tocsr()
        rng = np.random.default_rng(self.seed)
        self.user_factors = (rng.standard_normal((r.shape[0], self.factors)) * 0.01).astype(
            np.float32
        )
        self.item_factors = (rng.standard_normal((r.shape[1], self.factors)) * 0.01).astype(
            np.float32
        )
        self.history = []
        for it in range(self.iterations):
            self.user_factors = cg_solve(
                self.user_factors, self.item_factors, r, self.alpha, self.lam, self.cg_steps
            )
            self.item_factors = cg_solve(
                self.item_factors, self.user_factors, rt, self.alpha, self.lam, self.cg_steps
            )
            if it in (0, self.iterations // 2, self.iterations - 1):
                self.history.append((it + 1, self.loss(r)))
                log.info("ALS iteration %d loss %.4g", it + 1, self.history[-1][1])
        return self

    def loss(self, r: sp.csr_matrix) -> float:
        """The weighted objective, computed without materializing users x items:
        sum over all pairs of (x.y)^2, plus the extra terms on observed pairs."""
        x, y = self.user_factors.astype(np.float64), self.item_factors.astype(np.float64)
        all_pairs = float(np.sum((x.T @ x) * (y.T @ y)))
        pred = _pair_dots(self.user_factors, self.item_factors, r).astype(np.float64)
        observed = np.sum((1 + self.alpha) * (1 - pred) ** 2 - pred**2)
        reg = self.lam * (np.sum(x * x) + np.sum(y * y))
        return all_pairs + observed + reg

    def score(self, history: sp.csr_matrix, users: np.ndarray) -> np.ndarray:
        return self.user_factors[users] @ self.item_factors.T

    def fold_in(self, liked: np.ndarray, item_factors: np.ndarray | None = None) -> np.ndarray:
        """Exact user vector for a set of liked item indices (a visitor's session)."""
        y = self.item_factors if item_factors is None else item_factors
        ys = y[liked].astype(np.float64)
        a = y.T.astype(np.float64) @ y + self.alpha * ys.T @ ys + self.lam * np.eye(y.shape[1])
        b = (1 + self.alpha) * ys.sum(axis=0)
        return np.linalg.solve(a, b).astype(np.float32)
