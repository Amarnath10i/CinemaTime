"""Each model checked against its mathematical definition on small data."""

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

from cinemaml.data import Fold
from cinemaml.evaluate import recommend
from cinemaml.metrics import user_metrics
from cinemaml.models import ALS, EASE, Content, ItemKNN, Popularity
from cinemaml.models.als import cg_solve
from cinemaml.models.ease import ease_weights


def planted(n_users=400, n_items=60, rank=3, seed=0):
    """Users like items whose hidden taste vectors point the same way."""
    rng = np.random.default_rng(seed)
    u = rng.standard_normal((n_users, rank))
    v = rng.standard_normal((n_items, rank))
    score = u @ v.T + 0.3 * rng.standard_normal((n_users, n_items))
    liked = score > np.quantile(score, 0.85, axis=1, keepdims=True)
    hold = rng.random(liked.shape) < 0.2
    train = sp.csr_matrix((liked & ~hold).astype(np.float32))
    users = np.arange(n_users)
    truth = [np.flatnonzero(liked[i] & hold[i]) for i in users]
    keep = [i for i in users if len(truth[i])]
    pop = np.asarray(train.sum(axis=0)).ravel()
    fold = Fold(
        "toy",
        pd.Timestamp(0),
        pd.Timestamp(1),
        train,
        np.array(keep),
        [truth[i] for i in keep],
        pop,
        pop,
        train,  # every like is "1 day old"
    )
    return fold


class _Items:
    def __init__(self, n, d=8, seed=1):
        rng = np.random.default_rng(seed)
        c = rng.standard_normal((n, d)).astype(np.float32)
        self.content = c / np.linalg.norm(c, axis=1, keepdims=True)


def mean_recall(model, fold, k=10):
    recs = recommend(model, fold, fold.users, k)
    return np.mean([user_metrics(r, t, k)[0] for r, t in zip(recs, fold.truth, strict=True)])


def test_ease_columns_are_ridge_regressions_with_zero_diagonal():
    rng = np.random.default_rng(0)
    x = (rng.random((50, 8)) < 0.3).astype(float)
    lam = 2.0
    b = ease_weights(x.T @ x, lam)
    assert np.allclose(np.diag(b), 0)
    for j in range(8):
        others = [i for i in range(8) if i != j]
        xo = x[:, others]
        ridge = np.linalg.solve(xo.T @ xo + lam * np.eye(7), xo.T @ x[:, j])
        np.testing.assert_allclose(b[others, j], ridge, atol=1e-10)


def test_itemknn_similarity_matches_definition():
    fold = planted()
    m = ItemKNN(neighbors=59, shrink=5.0).fit(fold, _Items(60))
    x = fold.train.toarray()
    for i, j in [(0, 1), (3, 17), (40, 2)]:
        n_i, n_j = x[:, i].sum(), x[:, j].sum()
        expect = (x[:, i] @ x[:, j]) / (np.sqrt(n_i * n_j) + 5.0)
        assert m.sim[i, j] == pytest.approx(expect, rel=1e-5)


def test_cg_converges_to_the_exact_user_solution():
    rng = np.random.default_rng(2)
    m = sp.csr_matrix((rng.random((30, 20)) < 0.2).astype(np.float32))
    y = rng.standard_normal((20, 5)).astype(np.float32)
    alpha, lam = 10.0, 1.0
    x = cg_solve(np.zeros((30, 5), np.float32), y, m, alpha, lam, steps=25)
    for u in range(30):
        items = m.indices[m.indptr[u] : m.indptr[u + 1]]
        ys = y[items].astype(float)
        a = y.T @ y + alpha * ys.T @ ys + lam * np.eye(5)
        exact = np.linalg.solve(a, (1 + alpha) * ys.sum(axis=0))
        np.testing.assert_allclose(x[u], exact, rtol=1e-3, atol=1e-4)


def test_als_loss_never_increases_and_fold_in_matches_training_step():
    fold = planted()
    als = ALS(factors=6, alpha=10, lam=1, iterations=8, cg_steps=25).fit(fold)
    losses = [loss for _, loss in als.history]
    assert all(b <= a * (1 + 1e-6) for a, b in zip(losses, losses[1:], strict=False))
    # with converged CG, the trained user vector is the exact solve given item factors
    u = 7
    liked = fold.train.indices[fold.train.indptr[u] : fold.train.indptr[u + 1]]
    fresh = als.fold_in(liked)
    expect = cg_solve(
        als.user_factors[[u]], als.item_factors, fold.train[[u]], als.alpha, als.lam, 30
    )[0]
    np.testing.assert_allclose(fresh, expect, rtol=1e-3, atol=1e-4)


def test_collaborative_models_beat_popularity_on_planted_tastes():
    fold = planted()
    items = _Items(60)
    pop = mean_recall(Popularity().fit(fold, items), fold)
    for model in (EASE(lam=20.0), ItemKNN(neighbors=30, shrink=5.0), ALS(factors=6, iterations=10)):
        assert mean_recall(model.fit(fold, items), fold) > pop + 0.1, model.name


def test_content_profile_of_one_item_is_that_item():
    items = _Items(10)
    m = Content().fit(None, items)
    h = sp.csr_matrix(([1.0], ([0], [3])), shape=(1, 10))
    scores = m.score(h, np.array([0]))[0]
    assert scores.argmax() == 3 and scores[3] == pytest.approx(1.0, abs=1e-6)


def test_decay_halves_weight_every_half_life():
    fold = planted()
    ages = fold.train.copy()
    ages.data = np.array(
        [0.0, 365.0, 730.0] * (ages.nnz // 3) + [0.0] * (ages.nnz % 3), dtype=np.float32
    )
    fold.age_days = ages
    w = fold.decayed(365.0).data
    np.testing.assert_allclose(w[:3], [1.0, 0.5, 0.25], rtol=1e-6)
    assert fold.decayed(None) is fold.train


def test_content_map_recovers_a_linear_relationship():
    from cinemaml.models.hybrid import content_to_factors

    rng = np.random.default_rng(3)
    c = rng.standard_normal((500, 12))
    w_true = rng.standard_normal((12, 4))
    y = c @ w_true + 0.01 * rng.standard_normal((500, 4))
    np.testing.assert_allclose(content_to_factors(c, y, mu=1e-6), w_true, atol=0.01)


def test_hybrid_scores_cold_items_and_keeps_warm_ones():
    from cinemaml.models.hybrid import HybridALS

    fold = planted()
    items = _Items(60)
    fold.item_pop = fold.item_pop.copy()
    fold.item_pop[:5] = 0  # pretend the first five movies were never liked
    als = ALS(factors=6, iterations=5).fit(fold)
    hybrid = HybridALS(als, mu=1.0, min_likes=1).fit(fold, items)
    cold = fold.is_cold()  # the five we zeroed, plus any movie nobody happened to like
    assert cold[:5].all()
    np.testing.assert_array_equal(hybrid.item_factors[~cold], als.item_factors[~cold])
    np.testing.assert_allclose(hybrid.item_factors[cold], items.content[cold] @ hybrid.w, rtol=1e-5)
