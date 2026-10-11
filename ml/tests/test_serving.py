"""What the API serves must be what was evaluated.

The engine in backend/recsys/ is loaded from exported files and uses NumPy
only; given the same likes it has to reproduce the offline two-stage ranker
(LightGBM, SciPy, the training classes) score for score.
"""

import sys

import numpy as np
import pandas as pd
import pytest

from cinemaml import export
from cinemaml.config import REPO
from cinemaml.data import Items
from cinemaml.models import ALS, EASE, Content, Popularity
from cinemaml.models.hybrid import HybridALS
from cinemaml.models.ranker import TwoStage

sys.path.insert(0, str(REPO / "backend"))
from recsys.engine import Engine  # noqa: E402
from test_models import planted  # noqa: E402

PER_SOURCE = {"ease": 12, "als": 12, "popularity": 6, "content": 6}


def toy_items(n: int, seed: int = 4) -> Items:
    rng = np.random.default_rng(seed)
    genres = np.array(["Action", "Comedy", "Drama", "Horror", "Romance"])
    year = rng.integers(1960, 2024, n).astype(np.float64)
    year[rng.random(n) < 0.05] = np.nan  # unknown release dates exist in the catalog
    table = pd.DataFrame(
        {
            "catalog_id": [f"tmdb_{1000 + i}" for i in range(n)],
            "year": year,
            "released": pd.to_datetime(pd.Series(year).map(lambda y: None if np.isnan(y) else f"{y:.0f}-06-01")),
            "genres": [", ".join(rng.choice(genres, rng.integers(1, 3), replace=False)) for _ in range(n)],
        }
    )  # fmt: skip
    c = rng.standard_normal((n, 16)).astype(np.float32)
    return Items(table, c / np.linalg.norm(c, axis=1, keepdims=True))


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    fold = planted(n_users=300, n_items=80, rank=4, seed=5)
    items = toy_items(80)
    als = ALS(factors=4, alpha=10.0, lam=1.0, iterations=6, cg_steps=5).fit(fold)
    # a visitor's ALS vector is solved exactly at request time; give the
    # training users the same exact solve so both sides see identical inputs
    for u in range(fold.train.shape[0]):
        liked = fold.train.indices[fold.train.indptr[u] : fold.train.indptr[u + 1]]
        als.user_factors[u] = als.fold_in(liked)
    retrievers = {
        "ease": EASE(lam=10.0).fit(fold, items),
        "als": HybridALS(als, mu=1.0, min_likes=1).fit(fold, items),
        "popularity": Popularity(recent=True).fit(fold, items),
        "content": Content().fit(fold, items),
    }
    ranker = TwoStage(retrievers, PER_SOURCE, {"min_data_in_leaf": 20, "num_threads": 1})
    ranker.fit(fold, items, valid_share=0.3)
    directory = tmp_path_factory.mktemp("artifacts")
    export.write(directory, fold, items, retrievers, ranker.booster, PER_SOURCE)
    return fold, items, retrievers, ranker, Engine.load(items.content, directory)


def test_engine_reproduces_the_offline_two_stage_ranker(served):
    fold, _, _, ranker, engine = served
    users = fold.users[:60]
    offline = ranker.score(fold.train[users], users)
    liked = [fold.train[u].indices for u in users]
    r, c, s, _ = engine.rank(liked)
    online = np.full_like(offline, -np.inf)
    online[r, c] = s
    np.testing.assert_array_equal(np.isfinite(online), np.isfinite(offline))  # same candidates
    np.testing.assert_allclose(
        online[np.isfinite(online)], offline[np.isfinite(offline)], rtol=1e-5, atol=1e-6
    )
    # and therefore the same lists (compared by score: trees produce exact ties)
    top = engine.top(liked, 10)
    for row in range(len(users)):
        expect = np.sort(offline[row])[::-1][:10]
        np.testing.assert_allclose(online[row, top[row]], expect, rtol=1e-5, atol=1e-6)


def test_ease_scores_are_the_weighted_sum_of_liked_rows(served):
    _, _, retrievers, _, engine = served
    b = retrievers["ease"].b
    liked = np.array([3, 17, 42])
    w = np.array([1.0, 0.5, 0.25])
    np.testing.assert_allclose(engine.ease_scores(liked, w), w @ b[liked], rtol=1e-5, atol=1e-7)


def test_explanations_name_the_largest_ease_contribution(served):
    fold, items, retrievers, _, engine = served
    b = retrievers["ease"].b
    liked_idx = fold.train[fold.users[0]].indices
    ids = items.table["catalog_id"].to_numpy()
    recs = engine.recommend(list(ids[liked_idx]) + ["tmdb_unknown"], n=8)
    assert len(recs) == 8 and not set(r.item for r in recs) & set(liked_idx)
    for rec in recs:
        contrib = b[liked_idx, rec.item]
        if contrib.max() > 0:
            assert rec.because == liked_idx[contrib.argmax()]
        else:
            assert rec.because is None
        assert rec.similar in liked_idx


def test_a_visitor_without_likes_gets_last_years_favourites(served):
    fold, _, _, _, engine = served
    recs = engine.recommend([], n=5)
    assert [fold.recent_pop[r.item] for r in recs] == sorted(fold.recent_pop, reverse=True)[:5]


def test_unreleased_movies_are_never_recommended(served):
    from datetime import date

    fold, items, _, _, engine = served
    ids = items.table["catalog_id"].to_numpy()
    liked = list(ids[fold.train[fold.users[1]].indices])
    early = date(1990, 1, 1)
    released = items.table["released"]
    for rec in engine.recommend(liked, n=20, today=early):
        assert pd.isna(released[rec.item]) or released[rec.item] <= pd.Timestamp(early)


def test_engine_refuses_artifacts_with_other_features(served, tmp_path):
    import json

    fold, items, retrievers, ranker, _ = served
    export.write(tmp_path, fold, items, retrievers, ranker.booster, PER_SOURCE)
    meta = json.loads((tmp_path / "meta.json").read_text())
    meta["features"] = meta["features"][:-1]
    (tmp_path / "meta.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="re-export"):
        Engine.load(items.content, tmp_path)
