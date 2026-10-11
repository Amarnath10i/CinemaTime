"""Ranking movies nobody had rated yet.

Some of what test users went on to like were movies with no likes before the
cutoff, mostly new releases. Collaborative models cannot score them at all.
This experiment ranks *only* those cold movies (released before the window
closed) for each user who later liked one, comparing:

* random order (what a collaborative model effectively gives them),
* newest first,
* content similarity to the user's likes (CinemaTime today),
* the hybrid: content mapped into the ALS taste space by ridge regression,
  with the ridge strength mu chosen on the validation fold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cinemaml.experiments.common import best_params, fitted_als, fold, items, write_report
from cinemaml.metrics import bootstrap, top_k, user_metrics
from cinemaml.models import Content
from cinemaml.models.hybrid import HybridALS

MUS = (0.1, 1.0, 10.0, 100.0)


def cold_ranking(scores_fn, f, it, k=20) -> dict[str, np.ndarray]:
    cold = np.flatnonzero(f.is_cold() & ~f.unavailable())
    keep = [i for i, t in enumerate(f.truth) if np.isin(t, cold).any()]
    users = f.users[keep]
    recall, ndcg = [], []
    for s in range(0, len(users), 1024):
        u = users[s : s + 1024]
        sc = np.asarray(scores_fn(f.train[u], u))[:, cold]
        recs = cold[top_k(sc, k)]
        for row, i in enumerate(keep[s : s + 1024]):
            t = f.truth[i][np.isin(f.truth[i], cold)]
            r, n, _ = user_metrics(recs[row], t, k)
            recall.append(r)
            ndcg.append(n)
    return {"recall@20": np.array(recall), "ndcg@20": np.array(ndcg)}


def run() -> str:
    best, it = best_params(), items()
    year = np.nan_to_num(it.table["year"].to_numpy(np.float64), nan=1900.0)
    rng = np.random.default_rng(0)

    def methods(f, als, mu):
        hybrid = HybridALS(als, mu=mu).fit(f, it)
        content = Content().fit(f, it)
        noise = rng.random(f.n_items)
        return {
            "random order": lambda h, u: np.broadcast_to(noise, (len(u), f.n_items)),
            "newest first": lambda h, u: np.broadcast_to(year + 1e-3 * noise, (len(u), f.n_items)),
            "content similarity (CinemaTime today)": content.score,
            f"hybrid: content -> ALS space (mu={mu:g})": hybrid.score,
        }

    valid = fold("valid")
    als_valid = fitted_als("valid", best["als"])
    choose = {}
    for mu in MUS:
        hybrid = HybridALS(als_valid, mu=mu).fit(valid, it)
        choose[mu] = cold_ranking(hybrid.score, valid, it)["ndcg@20"].mean()
    mu = max(choose, key=choose.get)

    test = fold("test")
    als_test = fitted_als("test", best["als"])
    rows = []
    for name, fn in methods(test, als_test, mu).items():
        ci = bootstrap(cold_ranking(fn, test, it))
        rows.append(
            {"method": name} | {k: f"{v[0]:.4f} ({v[1]:.4f}-{v[2]:.4f})" for k, v in ci.items()}
        )
    n_cold = int((test.is_cold() & ~test.unavailable()).sum())
    held_out = np.concatenate(test.truth)
    cold_share = test.is_cold()[held_out].mean()
    users = len(cold_ranking(lambda h, u: np.zeros((len(u), test.n_items)), test, it)["recall@20"])
    text = "\n".join(
        [
            "# Cold start: ranking movies with no ratings yet (test fold)",
            "",
            f"{n_cold:,} catalog movies released by {test.window_end:%Y-%m-%d} had no likes "
            f"before {test.cutoff:%Y-%m-%d}, yet they make up {cold_share:.1%} of the likes "
            f"held out for evaluation; {users:,} test users liked at least one of them. Each "
            "method ranks only those cold movies for each such user; 95% bootstrap intervals "
            "over users.",
            "",
            pd.DataFrame(rows).to_markdown(index=False),
            "",
            "Ridge strength chosen on the validation fold (NDCG@20 there): "
            + ", ".join(f"mu={m:g}: {v:.4f}" for m, v in choose.items()),
            "",
        ]
    )
    write_report("coldstart", text)
    return text
