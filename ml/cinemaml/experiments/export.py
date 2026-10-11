"""Ship the models, after checking that what ships is what was evaluated.

1. Pruning EASE. The dense item-item matrix is 300 MB; the API keeps each
   movie's strongest weights. What does that cost the retriever alone?
2. Replay. Export artifacts from the test fold's cutoff, with the ranker
   trained on the validation fold, and run the API's NumPy engine on every
   test user as if they were a visitor. The only remaining approximation is
   ALS: a visitor's vector is solved at request time instead of trained.
3. Skew. The same replay for a ranker trained on the dense EASE's features
   but served with the pruned one: what mixing the two would have cost.
4. Short histories. A visitor has liked a handful of movies, not rated
   hundreds over a decade. Replay each test user's most recent m likes only.
5. Latency of one request inside the engine.
6. Ship. Refit the retrievers on every like, train the ranker on the most
   recent year (the same one-year shift that was evaluated: retrievers fitted
   at a cutoff, ranker trained on the year before it), and write
   backend/recsys/artifacts/.
"""

from __future__ import annotations

import gc
import json
import logging
import sys
import time
from datetime import date

import numpy as np
import pandas as pd

from cinemaml import export
from cinemaml.config import REPO, settings
from cinemaml.evaluate import evaluate
from cinemaml.experiments.common import (
    PER_SOURCE,
    SERVE_KEEP,
    best_params,
    fold,
    items,
    retrievers,
    trained_ranker,
    write_report,
)
from cinemaml.metrics import bootstrap, paired_difference, top_k, user_metrics
from cinemaml.models import EASE
from cinemaml.models.ease import signed_sparsify
from cinemaml.models.ranker import used_trees

sys.path.insert(0, str(REPO / "backend"))
from recsys.engine import Engine  # noqa: E402

log = logging.getLogger(__name__)

KEEPS = (50, 100, 200, 500)
SHORT = (1, 3, 5, 10, 20)
BATCH = 128
METRICS = ("ndcg@20", "recall@20", "recall@50")


def list_metrics(recs: np.ndarray, truth: list[np.ndarray]) -> dict[str, np.ndarray]:
    out = {m: np.empty(len(truth)) for m in METRICS}
    for i, t in enumerate(truth):
        out["recall@20"][i], out["ndcg@20"][i], _ = user_metrics(recs[i], t, 20)
        out["recall@50"][i] = user_metrics(recs[i], t, 50)[0]
    return out


def replay(engine: Engine, f, liked, weights=None) -> dict[str, np.ndarray]:
    gone = f.unavailable()
    recs = np.vstack([
        engine.top(liked[s : s + BATCH], 50, None if weights is None else weights[s : s + BATCH], gone)
        for s in range(0, len(liked), BATCH)
    ])  # fmt: skip
    return list_metrics(recs, f.truth)


def histories(f, half_life: float | None):
    """Each evaluated user's likes, and their EASE recency weights."""
    decayed = f.decayed(half_life)
    liked = [f.train.indices[f.train.indptr[u] : f.train.indptr[u + 1]] for u in f.users]
    weights = [decayed.data[decayed.indptr[u] : decayed.indptr[u + 1]] for u in f.users]
    return liked, weights


def most_recent(f, m: int) -> list[np.ndarray]:
    out = []
    for u in f.users:
        lo, hi = f.age_days.indptr[u], f.age_days.indptr[u + 1]
        newest = np.argsort(f.age_days.data[lo:hi], kind="stable")[:m]
        out.append(f.age_days.indices[lo:hi][newest])
    return out


def fmt(ci: tuple[float, float, float]) -> str:
    return f"{ci[0]:.4f} ({ci[1]:.4f}-{ci[2]:.4f})"


def diff(a: np.ndarray, b: np.ndarray) -> str:
    d, lo, hi = paired_difference(a, b)
    return f"{d:+.4f} ({lo:+.4f} to {hi:+.4f})"


def row(name: str, per_user: dict[str, np.ndarray], **extra) -> dict:
    ci = bootstrap({k: per_user[k] for k in METRICS})
    return {"model": name} | {k: fmt(ci[k]) for k in METRICS} | extra


def run() -> str:
    best, it = best_params(), items()
    test = fold("test")
    scratch = settings.paths.cache / "replay"
    liked, weights = histories(test, best["ease"].get("half_life_days"))
    gone = test.unavailable()

    # 2. replay: offline two-stage vs the API's engine, same artifacts --------
    ranker = trained_ranker("valid", best)
    final = retrievers(test, it, best)
    offline = evaluate(ranker.set_fold(test, it, final), test, it).per_user
    export.write(scratch / "consistent", test, it, final, ranker.booster, PER_SOURCE)
    engine = Engine.load(it.content, scratch / "consistent")
    t0 = time.perf_counter()
    served = replay(engine, test, liked, weights)
    log.info("replay: %.0fs", time.perf_counter() - t0)
    flat = replay(engine, test, liked)  # a live visitor's likes are all recent: weight 1

    # 4. short histories ---------------------------------------------------
    short_rows = []
    for m in SHORT:
        recent = most_recent(test, m)
        lists: dict[str, list] = {
            "popularity (last year)": [], "content (CinemaTime before)": [], "EASE alone": [],
            "ALS fold-in alone": [], "two-stage engine": [],
        }  # fmt: skip
        for s in range(0, len(recent), BATCH):
            batch = recent[s : s + BATCH]
            _, scores = engine.retrieve(batch, excluded=gone)
            lists["popularity (last year)"].append(top_k(scores["popularity"], 50))
            lists["content (CinemaTime before)"].append(top_k(scores["content"], 50))
            lists["EASE alone"].append(top_k(scores["ease"], 50))
            lists["ALS fold-in alone"].append(top_k(scores["als"], 50))
            lists["two-stage engine"].append(engine.top(batch, 50, excluded=gone))
        short_rows.append(
            {"likes given": m}
            | {name: list_metrics(np.vstack(p), test.truth)["ndcg@20"].mean() for name, p in lists.items()}
        )  # fmt: skip
        log.info("short history %d: %s", m, short_rows[-1])

    # 5. latency -------------------------------------------------------------
    rng = np.random.default_rng(0)
    ids = it.table["catalog_id"].to_numpy()
    warm = np.flatnonzero(test.item_pop >= 20)
    timings = []
    for _ in range(300):
        visitor = list(ids[rng.choice(warm, 10, replace=False)])
        t0 = time.perf_counter()
        engine.recommend(visitor, n=20, today=date(2023, 10, 14))
        timings.append((time.perf_counter() - t0) * 1000)
    p50, p95 = np.percentile(timings, [50, 95])

    # 3. skew: ranker trained on dense-EASE features, served pruned ----------
    dense_ranker = trained_ranker("valid", best, keep=None)
    dense_final = retrievers(test, it, best, keep=None)
    offline_dense = evaluate(dense_ranker.set_fold(test, it, dense_final), test, it).per_user
    export.write(scratch / "skewed", test, it, final, dense_ranker.booster, PER_SOURCE)
    skewed = replay(Engine.load(it.content, scratch / "skewed"), test, liked, weights)

    # 1. what pruning costs EASE on its own -----------------------------------
    dense = dense_final["ease"]
    dense_eval = evaluate(dense, test, it).per_user
    ease_rows = [
        row(
            dense.name,
            dense_eval,
            **{"weights (MB)": f"{dense.b.size * 4 / 1e6:.0f}"},
        )
    ]
    for keep in KEEPS:
        pruned = EASE(**best["ease"], keep=keep)
        pruned.fold, pruned.b = test, signed_sparsify(dense.b, keep)
        ease_rows.append(row(pruned.name, evaluate(pruned, test, it).per_user,
                             **{"weights (MB)": f"{pruned.b.nnz * 8 / 1e6:.1f}"}))  # fmt: skip
    ease_cost = paired_difference(
        dense_eval["ndcg@20"],
        evaluate(final["ease"], test, it).per_user["ndcg@20"],
    )[0]
    del dense_final, dense, dense_ranker
    gc.collect()

    replay_rows = [
        row(f"offline two-stage, EASE top {SERVE_KEEP} (LightGBM, SciPy)", offline, **{"vs offline": "-"}),
        row("served: API engine on exported arrays (NumPy)", served, **{"vs offline": diff(offline["ndcg@20"], served["ndcg@20"])}),
        row("served, likes sent without recency weights", flat, **{"vs offline": diff(offline["ndcg@20"], flat["ndcg@20"])}),
    ]  # fmt: skip
    skew_rows = [
        row("ranker trained on dense-EASE features, offline with dense EASE", offline_dense, **{"vs consistent served": "-"}),
        row(f"same ranker served with EASE top {SERVE_KEEP} (skew)", skewed, **{"vs consistent served": diff(served["ndcg@20"], skewed["ndcg@20"])}),
        row(f"ranker trained on EASE top {SERVE_KEEP} features, served the same", served, **{"vs consistent served": "-"}),
    ]  # fmt: skip

    # 6. ship ---------------------------------------------------------------
    replay_summary_skew = paired_difference(offline_dense["ndcg@20"], skewed["ndcg@20"])[0]
    shipped_ranker = trained_ranker("test", best, final)
    full = fold("full")
    replay_summary = {
        "users": len(test.users),
        "ease_keep": SERVE_KEEP,
        "ndcg@20": float(served["ndcg@20"].mean()),
        "recall@20": float(served["recall@20"].mean()),
        "offline_ndcg@20": float(offline["ndcg@20"].mean()),
        "skewed_ndcg@20": float(skewed["ndcg@20"].mean()),
        "short_history_ndcg@20": short_rows,
        "latency_ms": {"p50": float(p50), "p95": float(p95)},
    }
    results = settings.paths.reports / "results.json"
    full_retrievers = retrievers(full, it, best)
    sizes = export.write(
        settings.paths.export / "artifacts",
        full,
        it,
        full_retrievers,
        shipped_ranker.booster,
        PER_SOURCE,
        {"exported": str(date.today()),
         "offline": json.loads(results.read_text()) if results.exists() else None,
         "replay": replay_summary},
    )  # fmt: skip
    trees = used_trees(shipped_ranker.booster)

    text = "\n".join(
        [
            "# Serving: is what ships what was evaluated?",
            "",
            f"Test fold: models see likes before {test.cutoff:%Y-%m-%d}; {len(test.users):,} users are "
            f"scored on what they liked until {test.window_end:%Y-%m-%d}. 95% bootstrap intervals over "
            "users; differences are paired over the same users.",
            "",
            "## 1. Pruning EASE for serving",
            "",
            "The dense item-item matrix is too big for a small serverless function. Keeping each "
            "movie's strongest weights (by magnitude, sign preserved), EASE alone:",
            "",
            pd.DataFrame(ease_rows).to_markdown(index=False),
            "",
            "## 2. Replaying the test users through the API's engine",
            "",
            f"Artifacts exported from the {test.cutoff:%Y-%m-%d} cutoff, ranker trained on the "
            "validation fold with the same pruned EASE; every test user sent as a visitor with their "
            "full history. What remains different is ALS: the engine solves each visitor's vector at "
            "request time, the offline model uses the trained one.",
            "",
            pd.DataFrame(replay_rows).to_markdown(index=False),
            "",
            "## 3. Training-serving skew, measured",
            "",
            "An earlier version trained the ranker on features from the dense EASE and served the "
            f"pruned one. Pruning to the top {SERVE_KEEP} weights changes EASE's own NDCG@20 by "
            f"{ease_cost:+.4f}. A ranker trained on the dense EASE's features but served the pruned "
            f"EASE changes the two-stage NDCG@20 by {replay_summary_skew:+.4f}: its thresholds on "
            "`ease_rank` and `ease_rel` were learned on the dense distribution, which pruning shifts "
            "(thousands of small weights become exactly zero). The loss is small but avoidable: the "
            "ranker trained on the pruned EASE it is served with matches the dense pipeline.",
            "",
            pd.DataFrame(skew_rows).to_markdown(index=False),
            "",
            "## 4. Visitors with only a few likes",
            "",
            "Each test user replayed with only their *m* most recent likes before the cutoff (users "
            "with fewer give all of theirs). NDCG@20 against the same held-out year.",
            "",
            pd.DataFrame(short_rows).to_markdown(index=False, floatfmt=".4f"),
            "",
            "## 5. Latency",
            "",
            f"One request (10 likes, top 20 with explanations), engine only, in-process: "
            f"p50 {p50:.1f} ms, p95 {p95:.1f} ms over 300 requests on a laptop CPU.",
            "",
            "## 6. Shipped artifacts",
            "",
            f"Retrievers refitted on every like until {full.cutoff:%Y-%m-%d}; ranker trained on the "
            f"{test.cutoff:%Y-%m-%d} to {test.window_end:%Y-%m-%d} window ({trees} trees).",
            "",
            *[f"- `backend/recsys/artifacts/{name}`: {size / 1e6:.1f} MB" for name, size in sorted(sizes.items())],
            "",
        ]
    )  # fmt: skip
    write_report("serving", text)
    return text
