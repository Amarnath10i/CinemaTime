"""The NumPy evaluator used in production must equal LightGBM exactly."""

import sys

import lightgbm as lgb
import numpy as np
import pytest

from cinemaml.config import REPO

sys.path.insert(0, str(REPO / "backend"))
from recsys.trees import TreeEnsemble  # noqa: E402


@pytest.mark.parametrize("objective", ["lambdarank", "binary", "regression"])
def test_numpy_trees_match_lightgbm(objective):
    rng = np.random.default_rng(0)
    n, d = 3000, 6
    x = rng.standard_normal((n, d))
    x[rng.random((n, d)) < 0.1] = np.nan  # missing values take the default branch
    x[:, 5] = np.where(rng.random(n) < 0.3, 0.0, x[:, 5])  # exact zeros
    y = ((np.nan_to_num(x[:, 0]) + np.nan_to_num(x[:, 1]) ** 2) > 0.5).astype(float)
    params = {"objective": objective, "verbose": -1, "num_leaves": 15, "min_data_in_leaf": 20}
    if objective == "lambdarank":
        ds = lgb.Dataset(x, y, group=[30] * (n // 30))
    else:
        ds = lgb.Dataset(x, y)
    booster = lgb.train(params, ds, 40)
    ours = TreeEnsemble(booster.dump_model()).predict(x)
    np.testing.assert_allclose(ours, booster.predict(x, raw_score=True), rtol=1e-9, atol=1e-9)
