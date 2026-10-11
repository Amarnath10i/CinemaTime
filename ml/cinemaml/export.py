"""Write the arrays the API's recommender (backend/recsys/engine.py) serves.

model.npz holds every array, meta.json the hyperparameters, the feature list
the ranker was trained with (the engine refuses to load on a mismatch) and
the offline results the model card shows. Content vectors are not copied:
the API already has them in its FAISS index.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from cinemaml.config import REPO
from cinemaml.data import Fold, Items
from cinemaml.models.ranker import genre_matrix, genre_names, used_trees

sys.path.insert(0, str(REPO / "backend"))
from recsys.features import FEATURES  # noqa: E402
from recsys.trees import TreeEnsemble  # noqa: E402


def released_days(items: Items) -> np.ndarray:
    """Release date as days since 1970; unknown dates count as long released."""
    released = pd.to_datetime(items.table["released"])
    days = (released - pd.Timestamp("1970-01-01")).dt.days
    return days.fillna(np.iinfo(np.int32).min).to_numpy(np.int32)


def write(
    directory: Path,
    fold: Fold,
    items: Items,
    retrievers: dict,
    booster,
    per_source: dict[str, int],
    extra_meta: dict | None = None,
) -> dict[str, int]:
    """Export fitted retrievers and a LightGBM ranker; returns file sizes in bytes.

    EASE is written as fitted: pruned to its top weights per movie (`keep`),
    which is what the ranker must have been trained with, or dense in tests.
    """
    ease, hybrid = retrievers["ease"], retrievers["als"]
    b = sp.csr_matrix(ease.b, dtype=np.float32)
    b.eliminate_zeros()
    b.sort_indices()  # the engine binary-searches rows for explanations

    als = hybrid.als
    y = als.item_factors.astype(np.float64)
    trees = TreeEnsemble(booster.dump_model(num_iteration=used_trees(booster)))

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        directory / "model.npz",
        catalog_ids=items.table["catalog_id"].to_numpy().astype(str),
        genres=genre_matrix(items).astype(np.uint8),
        year=items.table["year"].to_numpy(np.float64),
        released_day=released_days(items),
        item_pop=fold.item_pop.astype(np.float32),
        recent_pop=fold.recent_pop.astype(np.float32),
        ease_indptr=b.indptr.astype(np.int64),
        ease_indices=b.indices.astype(np.int32),
        ease_data=b.data.astype(np.float32),
        als_factors=hybrid.item_factors.astype(np.float32),
        als_gram=y.T @ y + als.lam * np.eye(y.shape[1]),
        **trees.arrays(),
    )
    meta = {
        "features": FEATURES,
        "per_source": per_source,
        "reference_year": int(fold.cutoff.year),
        "interactions_until": str(fold.cutoff.date()),
        "n_items": len(items),
        "genres": genre_names(items),
        "ease": {"lam": ease.lam, "half_life_days": ease.half_life_days, "keep": ease.keep,
                 "nonzeros": int(b.nnz)},
        "als": {"factors": als.factors, "alpha": als.alpha, "lam": als.lam,
                "content_map_mu": hybrid.mu},
        "ranker": {"trees": len(trees.roots), "nodes": len(trees.feature)},
    } | (extra_meta or {})  # fmt: skip
    (directory / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {p.name: p.stat().st_size for p in directory.iterdir()}
