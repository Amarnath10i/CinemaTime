import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cinemaml.metrics import beyond_accuracy, bootstrap, top_k, user_metrics


@settings(max_examples=200, deadline=None)
@given(st.lists(st.floats(-5, 5, allow_nan=False), min_size=3, max_size=40), st.integers(1, 10))
def test_top_k_returns_the_k_best_scores_in_order(values, k):
    # Items tied exactly at the cut-off are interchangeable; what must hold is
    # that the selected scores are the k largest, best first, without repeats.
    scores = np.array([values])
    got = top_k(scores, k)[0]
    k = min(k, len(values))
    assert len(set(got.tolist())) == k
    assert scores[0, got].tolist() == sorted(values, reverse=True)[:k]


def test_user_metrics_known_values():
    rec = np.array([5, 1, 9, 3, 7])
    truth = np.array([1, 3, 8])
    recall, ndcg, hit = user_metrics(rec, truth, k=5)
    assert recall == pytest.approx(2 / 3)
    dcg = 1 / np.log2(3) + 1 / np.log2(5)  # hits at ranks 1 and 3 (0-based)
    idcg = 1 + 1 / np.log2(3) + 1 / np.log2(4)
    assert ndcg == pytest.approx(dcg / idcg)
    assert hit == 1.0


def test_perfect_ranking_has_ndcg_one_and_misses_score_zero():
    truth = np.array([4, 2])
    assert user_metrics(np.array([2, 4, 0, 1]), truth, 4)[1] == pytest.approx(1.0)
    assert user_metrics(np.array([0, 1, 3]), truth, 3) == (0.0, 0.0, 0.0)


def test_ndcg_is_normalised_by_achievable_hits_at_k():
    # 10 relevant items but only 2 slots: two hits at the top is perfect
    assert user_metrics(np.array([0, 1]), np.arange(10), 2)[1] == pytest.approx(1.0)


def test_beyond_accuracy_extremes():
    content = np.eye(4, dtype=np.float32)  # every item orthogonal to every other
    recs = np.array([[0, 1], [2, 3]])
    m = beyond_accuracy(recs, item_pop=np.array([10, 1, 1, 1]), n_train_users=10, content=content)
    assert m["coverage"] == 1.0
    assert m["diversity_ild"] == pytest.approx(1.0)
    same = beyond_accuracy(np.array([[0, 0]]), np.array([10, 1, 1, 1]), 10, content)
    assert same["diversity_ild"] == pytest.approx(0.0)


def test_bootstrap_interval_contains_mean():
    rng = np.random.default_rng(0)
    v = rng.random(2000)
    mean, lo, hi = bootstrap({"m": v})["m"]
    assert lo < mean < hi and hi - lo < 0.05
