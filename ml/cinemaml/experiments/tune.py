"""Hyperparameter selection on the validation fold only (never the test fold).

Selection metric: NDCG@20. The grid is small on purpose: each choice below is
one an interviewer can ask about (regularization strength, how fast old
tastes should be forgotten, latent dimensionality).
"""

from __future__ import annotations

import json
import logging
import time

import pandas as pd

from cinemaml.evaluate import evaluate
from cinemaml.experiments.common import BEST, fitted_als, fold, items, write_report
from cinemaml.models import EASE, ItemKNN

log = logging.getLogger(__name__)

EASE_GRID = [
    (lam, hl) for lam in (250, 500, 1000, 2000) for hl in (None, 4 * 365, 2 * 365, 365, 182, 91)
]
ALS_GRID = [
    {"factors": 64, "alpha": 20.0, "lam": 10.0},
    {"factors": 128, "alpha": 20.0, "lam": 10.0},
    {"factors": 128, "alpha": 40.0, "lam": 50.0},
]
KNN_GRID = [(200, 50.0), (500, 100.0)]


class _Cached:
    """An already-fitted model; fit() is a no-op so cached ALS runs are reused."""

    def __init__(self, model) -> None:
        self.model, self.name = model, model.name
        self.fit_seconds = model.fit_seconds  # measured when it was first fitted

    def fit(self, fold, items):
        return self

    def score(self, history, users):
        return self.model.score(history, users)


def run() -> str:
    f, it = fold("valid"), items()
    rows, best = [], {}

    def record(family: str, params: dict, model) -> None:
        t0 = time.perf_counter()
        model.fit(f, it)
        fit_s = getattr(model, "fit_seconds", time.perf_counter() - t0)
        m = evaluate(model, f, it).means()
        rows.append(
            {"family": family, "model": model.name, "fit (s)": round(fit_s) if fit_s == fit_s else None,
             "recall@20": m["recall@20"], "ndcg@20": m["ndcg@20"], "coverage@10": m["coverage"]}
        )  # fmt: skip
        if m["ndcg@20"] > best.get(family, (None, -1.0))[1]:
            best[family] = (params, m["ndcg@20"])
        log.info("%s ndcg@20 %.4f", model.name, m["ndcg@20"])

    for lam, hl in EASE_GRID:
        record("ease", {"lam": lam, "half_life_days": hl}, EASE(lam=lam, half_life_days=hl))
    for neighbors, shrink in KNN_GRID:
        record("itemknn", {"neighbors": neighbors, "shrink": shrink}, ItemKNN(neighbors, shrink))
    for params in ALS_GRID:
        record("als", params, _Cached(fitted_als("valid", params)))

    chosen = {family: params for family, (params, _) in best.items()}
    BEST.parent.mkdir(parents=True, exist_ok=True)
    BEST.write_text(json.dumps(chosen, indent=2) + "\n")

    table = pd.DataFrame(rows).sort_values(["family", "ndcg@20"], ascending=[True, False])
    text = "\n".join(
        [
            "# Hyperparameter selection (validation fold)",
            "",
            f"Train on likes before {f.cutoff:%Y-%m-%d}, evaluate {len(f.users):,} users' likes "
            f"until {f.window_end:%Y-%m-%d}. Selection by NDCG@20; the test fold is not touched.",
            "",
            table.to_markdown(index=False, floatfmt=".4f"),
            "",
            "Chosen:",
            "",
            "```json",
            json.dumps(chosen, indent=2),
            "```",
            "",
        ]
    )
    write_report("tuning", text)
    return text
