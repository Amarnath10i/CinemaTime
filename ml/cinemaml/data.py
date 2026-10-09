"""MovieLens 32M joined to the CinemaTime catalog.

Items are *all* movies in CinemaTime's catalog (backend/movies.pkl). MovieLens
`links.csv` maps its movieIds to TMDB ids, which is how the catalog names
movies (`tmdb_<id>`); catalog movies without a MovieLens id (mostly 2020s
releases) simply have no interactions, i.e. they are cold-start items, which is
exactly the situation the production system faces.

A "like" is a rating of 4 stars or more. Each fold trains on likes strictly
before its cutoff and evaluates users' likes in the following window.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import faiss
import numpy as np
import pandas as pd
import scipy.sparse as sp

from cinemaml.config import settings

log = logging.getLogger(__name__)


@dataclass
class Items:
    table: (
        pd.DataFrame
    )  # item_idx, catalog_id, catalog_row, tmdb, movieId (nullable), title, year, genres
    content: np.ndarray  # (n_items, 384) float32 SBERT vectors, L2-normalized

    def __len__(self) -> int:
        return len(self.table)


def load_items() -> Items:
    p = settings.paths
    cache = p.cache / "items.parquet"
    catalog = pd.read_pickle(p.catalog).reset_index(drop=True)
    if cache.exists():
        table = pd.read_parquet(cache)
    else:
        movies = catalog[
            (catalog["media_type"] == "movie") & catalog["id"].str.match(r"^tmdb_\d+$")
        ]
        table = pd.DataFrame(
            {
                "catalog_id": movies["id"].to_numpy(),
                "catalog_row": movies.index.to_numpy(),
                "tmdb": movies["id"].str.removeprefix("tmdb_").astype("int64").to_numpy(),
                "title": movies["title"].to_numpy(),
                "year": pd.to_datetime(movies["release_date"], errors="coerce").dt.year.to_numpy(),
                "genres": movies["genres_display"].fillna("").to_numpy(),
            }
        ).drop_duplicates("catalog_id")
        links = pd.read_csv(p.raw / "links.csv", dtype={"tmdbId": "Int64"}).dropna(
            subset=["tmdbId"]
        )
        # a TMDB id occasionally maps to several MovieLens ids: keep the lowest
        links = links.sort_values("movieId").drop_duplicates("tmdbId")
        table = table.merge(
            links[["movieId", "tmdbId"]].rename(columns={"tmdbId": "tmdb"}), on="tmdb", how="left"
        )
        table = table.sort_values("catalog_id", kind="stable").reset_index(drop=True)
        table.insert(0, "item_idx", np.arange(len(table), dtype=np.int32))
        p.cache.mkdir(parents=True, exist_ok=True)
        table.to_parquet(cache, index=False)

    index = faiss.read_index(str(p.content_index))
    vectors = index.reconstruct_n(0, index.ntotal)[table["catalog_row"].to_numpy()]
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    return Items(table, vectors.astype(np.float32))


def load_likes(items: Items) -> pd.DataFrame:
    """All likes (rating >= 4) on catalog movies: user, item (item_idx), ts."""
    p = settings.paths
    cache = p.cache / "likes.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    log.info("reading ratings.csv (32M rows)")
    r = pd.read_csv(
        p.raw / "ratings.csv",
        dtype={"userId": "int32", "movieId": "int32", "rating": "float32", "timestamp": "int64"},
    )
    r = r[r["rating"] >= settings.protocol.positive_rating]
    mapped = items.table.dropna(subset=["movieId"])
    to_item = pd.Series(mapped["item_idx"].to_numpy(), index=mapped["movieId"].astype("int32"))
    r = r[r["movieId"].isin(to_item.index)]
    likes = pd.DataFrame(
        {
            "user": r["userId"].to_numpy(),
            "item": to_item.loc[r["movieId"].to_numpy()].to_numpy().astype(np.int32),
            "ts": pd.to_datetime(r["timestamp"].to_numpy(), unit="s"),
        }
    ).sort_values("ts", kind="stable", ignore_index=True)
    likes.to_parquet(cache, index=False)
    return likes


@dataclass
class Fold:
    name: str
    cutoff: pd.Timestamp
    window_end: pd.Timestamp
    train: sp.csr_matrix  # (n_users, n_items) binary likes before the cutoff
    users: np.ndarray  # evaluated users (row ids into `train`)
    truth: list[np.ndarray]  # their likes inside the window, not already in their history
    item_pop: np.ndarray  # likes per item before the cutoff
    recent_pop: np.ndarray  # likes per item in the 365 days before the cutoff

    @property
    def n_items(self) -> int:
        return self.train.shape[1]

    def is_cold(self) -> np.ndarray:
        """Items nobody had liked before the cutoff."""
        return self.item_pop == 0


def make_fold(
    likes: pd.DataFrame, n_items: int, cutoff: pd.Timestamp, window_end: pd.Timestamp, name: str
) -> Fold:
    proto = settings.protocol
    n_users = int(likes["user"].max()) + 1
    before = likes[likes["ts"] < cutoff]
    train = sp.csr_matrix(
        (
            np.ones(len(before), dtype=np.float32),
            (before["user"].to_numpy(), before["item"].to_numpy()),
        ),
        shape=(n_users, n_items),
    )
    train.sum_duplicates()
    train.data[:] = 1.0
    history = np.diff(train.indptr)

    window = likes[(likes["ts"] >= cutoff) & (likes["ts"] < window_end)]
    window = window[history[window["user"].to_numpy()] >= proto.min_history]
    users, truth = [], []
    for u, grp in window.groupby("user", sort=True):
        seen = train.indices[train.indptr[u] : train.indptr[u + 1]]
        t = np.setdiff1d(grp["item"].to_numpy(), seen)
        if len(t):
            users.append(u)
            truth.append(t.astype(np.int32))
    item_pop = np.asarray(train.sum(axis=0)).ravel()
    last_year = before[before["ts"] >= cutoff - pd.Timedelta(days=365)]
    recent_pop = np.bincount(last_year["item"].to_numpy(), minlength=n_items).astype(np.float64)
    log.info("fold %s: %d train likes, %d evaluated users", name, train.nnz, len(users))
    return Fold(
        name,
        cutoff,
        window_end,
        train,
        np.array(users, dtype=np.int64),
        truth,
        item_pop,
        recent_pop,
    )


def folds(likes: pd.DataFrame, n_items: int) -> dict[str, Fold]:
    p = settings.protocol
    return {
        "valid": make_fold(likes, n_items, p.valid_start, p.test_start, "valid"),
        "test": make_fold(likes, n_items, p.test_start, p.end, "test"),
    }
