"""Shared helpers: data loading once per process, report writing, best
parameters, and the fitted models several experiments reuse."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from functools import cache

from cinemaml.config import settings
from cinemaml.data import Fold, Items, load_items, load_likes, make_named_fold

log = logging.getLogger(__name__)

BEST = settings.paths.reports / "best_params.json"
# candidates each retriever contributes to the stage-2 ranker
PER_SOURCE = {"ease": 150, "als": 100, "popularity": 50, "content": 50}
# EASE weights kept per movie in the two-stage model. The dense matrix is
# 300 MB; the API has to fit a small serverless function, so the ranker is
# trained on, evaluated with and served with the pruned EASE, never a mix
# (reports/serving.md shows what a mix costs).
SERVE_KEEP = 200


@cache
def items() -> Items:
    return load_items()


@cache
def fold(name: str) -> Fold:
    return make_named_fold(load_likes(items()), items(), name)


def write_report(name: str, text: str) -> None:
    settings.paths.reports.mkdir(parents=True, exist_ok=True)
    (settings.paths.reports / f"{name}.md").write_text(text, encoding="utf-8")


def best_params() -> dict:
    return json.loads(BEST.read_text()) if BEST.exists() else {}


def fitted_als(fold_name: str, params: dict):
    """ALS fitted on a fold, cached on disk (each fit takes a few minutes)."""
    import numpy as np

    from cinemaml.models import ALS

    key = "_".join(f"{k}{v}" for k, v in sorted(params.items()))
    path = settings.paths.cache / f"als_{fold_name}_{key}.npz"
    model = ALS(**params, iterations=12)
    if path.exists():
        with np.load(path) as z:
            model.user_factors, model.item_factors = z["users"], z["items"]
            model.fit_seconds = float(z["seconds"]) if "seconds" in z.files else float("nan")
        return model
    t0 = time.perf_counter()
    model.fit(fold(fold_name), items())
    model.fit_seconds = time.perf_counter() - t0
    np.savez(path, users=model.user_factors, items=model.item_factors, seconds=model.fit_seconds)
    return model


def retrievers(f: Fold, it: Items, best: dict, keep: int | None = SERVE_KEEP) -> dict:
    """The four candidate sources of the two-stage model, fitted on one fold."""
    from cinemaml.models import EASE, Content, Popularity
    from cinemaml.models.hybrid import HybridALS

    return {
        "ease": EASE(**best["ease"], keep=keep).fit(f, it),
        "als": HybridALS(fitted_als(f.name, best["als"])).fit(f, it),
        "popularity": Popularity(recent=True).fit(f, it),
        "content": Content().fit(f, it),
    }


def trained_ranker(
    fold_name: str, best: dict, retr: dict | None = None, keep: int | None = SERVE_KEEP
):
    """The LambdaRank stage trained on one fold: retrievers fitted before its
    cutoff, labels = likes inside its window. Cached; the key covers
    everything that changes the training set. `retr`, if given, must have been
    fitted on that fold with the same `keep`."""
    import lightgbm as lgb

    from cinemaml.models.ranker import FEATURES, TwoStage

    f, it = fold(fold_name), items()
    ranker = TwoStage(retr or retrievers(f, it, best, keep), PER_SOURCE)
    spec = json.dumps([best, keep, PER_SOURCE, FEATURES, ranker.params], sort_keys=True)
    key = hashlib.sha1(spec.encode()).hexdigest()[:10]
    path = settings.paths.cache / f"ranker_{fold_name}_{key}.txt"
    side = path.with_suffix(".json")
    if path.exists() and side.exists():
        ranker.set_fold(f, it)
        ranker.booster = lgb.Booster(model_file=str(path))
        ranker.candidate_recall = json.loads(side.read_text())["candidate_recall"]
        return ranker
    ranker.fit(f, it)
    ranker.booster.save_model(str(path))
    side.write_text(json.dumps({"candidate_recall": float(ranker.candidate_recall)}))
    log.info("ranker on %s: %d trees", fold_name, ranker.booster.num_trees())
    return ranker
