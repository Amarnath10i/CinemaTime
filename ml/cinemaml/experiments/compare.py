"""Every model on the test fold: train on likes before Oct 2022, evaluate the
following year. Hyperparameters come from the validation fold (tune.py); the
ranker is trained on the validation fold and applied unchanged here."""

from __future__ import annotations

import json
import logging
import time

import pandas as pd

from cinemaml.config import settings
from cinemaml.evaluate import evaluate
from cinemaml.experiments.common import (
    PER_SOURCE,
    best_params,
    fold,
    items,
    retrievers,
    trained_ranker,
    write_report,
)
from cinemaml.metrics import bootstrap, paired_difference
from cinemaml.models import EASE, Content, ItemKNN, Popularity
from cinemaml.models.ranker import TwoStage

log = logging.getLogger(__name__)

SHOWN = ["recall@20", "ndcg@20", "hit@10", "recall@50"]


def run() -> str:
    best = best_params()
    it, test = items(), fold("test")

    # stage-2 ranker: retrievers and labels from the validation fold only
    ranker = trained_ranker("valid", best)
    valid_candidate_recall = ranker.candidate_recall

    final = retrievers(test, it, best)
    ease_best = EASE(**best["ease"])  # dense; the two-stage model uses final["ease"], pruned
    models = [
        Popularity(),
        Popularity(recent=True),
        Content(),
        ItemKNN(**best["itemknn"]),
        EASE(lam=best["ease"]["lam"]),
        ease_best,
        final["ease"],
        final["als"].als,
        final["als"],
        ranker.set_fold(test, it, final),
    ]
    results, fit_seconds = {}, {}
    for m in models:
        t0 = time.perf_counter()
        if not isinstance(m, TwoStage) and m not in final.values() and m is not final["als"].als:
            m.fit(test, it)
        fit_seconds[m.name] = time.perf_counter() - t0
        results[m.name] = evaluate(m, test, it)
        log.info("%s: %s", m.name, {k: round(v, 4) for k, v in results[m.name].means().items()})

    rows = []
    for name, r in results.items():
        ci = bootstrap({k: r.per_user[k] for k in SHOWN})
        means = r.means()
        rows.append(
            {"model": name}
            | {k: f"{ci[k][0]:.4f} ({ci[k][1]:.4f}-{ci[k][2]:.4f})" for k in SHOWN}
            | {"cold recall@50": f"{means['cold_recall@50']:.4f}",
               "coverage@10": f"{means['coverage']:.3f}",
               "novelty (bits)": f"{means['novelty_bits']:.2f}",
               "diversity@10": f"{means['diversity_ild']:.3f}"}
        )  # fmt: skip
    table = pd.DataFrame(rows)

    content, two_stage = results[Content.name], results[ranker.name]
    diffs = []
    for metric in ("recall@20", "ndcg@20"):
        for base_name, base in (
            ("current CinemaTime (content)", content),
            ("best single model (EASE)", results[ease_best.name]),
        ):
            d, lo, hi = paired_difference(base.per_user[metric], two_stage.per_user[metric])
            rel = d / base.per_user[metric].mean()
            diffs.append(
                f"| {metric} | {base_name} | {d:+.4f} ({lo:+.4f} to {hi:+.4f}) | {rel:+.0%} |"
            )

    summary = {
        "fold": {"train_until": str(test.cutoff.date()), "evaluate_until": str(test.window_end.date()),
                 "users": len(test.users), "held_out_likes": int(sum(len(t) for t in test.truth))},
        "models": {name: r.means() for name, r in results.items()},
        "fit_seconds": {name: round(sec, 1) for name, sec in fit_seconds.items()},
        "ranker": {"name": ranker.name, "valid_candidate_recall": float(valid_candidate_recall),
                   "trees": ranker.booster.best_iteration or ranker.booster.num_trees()},
    }  # fmt: skip
    (settings.paths.reports / "results.json").write_text(json.dumps(summary, indent=2))

    imp = pd.Series(ranker.booster.feature_importance("gain"), index=ranker.booster.feature_name())
    imp = (imp / imp.sum()).sort_values(ascending=False)
    text = "\n".join(
        [
            "# Model comparison (test fold)",
            "",
            f"Models train on likes (ratings >= 4) before {test.cutoff:%Y-%m-%d} and rank all "
            f"{test.n_items:,} catalog movies for {len(test.users):,} users, who are scored on the "
            f"{summary['fold']['held_out_likes']:,} movies they liked in the following year. Full "
            "ranking, no sampled negatives. Point estimate with a 95% bootstrap interval over users.",
            "",
            table.to_markdown(index=False),
            "",
            "## Two-stage ranker vs. alternatives (paired bootstrap over the same users)",
            "",
            "| metric | compared with | difference (95% interval) | relative |",
            "|---|---|---|---|",
            *diffs,
            "",
            f"The ranker re-orders candidates from {', '.join(f'{k} ({v})' for k, v in PER_SOURCE.items())}; "
            f"on the validation fold those candidates contained {valid_candidate_recall:.1%} of users' "
            "future likes, the ceiling for stage 2.",
            "",
            "## What the ranker relies on (share of split gain)",
            "",
            "| feature | share |",
            "|---|---|",
            *[f"| {k} | {v:.3f} |" for k, v in imp.items()],
            "",
        ]
    )
    write_report("model_comparison", text)
    return text
