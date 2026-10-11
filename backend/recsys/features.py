"""Ranker features, shared by offline training and the live API.

Training (ml/cinemaml/models/ranker.py) and serving (engine.py) both call
`build`, so a feature can never mean one thing in the notebook and another
in production. Only NumPy is used: the API runs on a small function host.

Every retriever score is divided by the user's best score from that
retriever. Raw EASE and ALS scores grow with the length and recency of a
user's history, which differ a lot between MovieLens users with years of
ratings and a visitor who liked five movies a minute ago; relative scores
and ranks mean the same thing for both.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FEATURES = [
    "ease_rel", "ease_rank", "als_rel", "als_rank", "content_score", "content_rank",
    "log_likes", "log_likes_last_year", "share_last_year", "is_cold", "age_years",
    "year_gap", "genre_overlap", "user_log_likes",
]  # fmt: skip
# Deliberately absent: "share of the user's likes from the last year". It varies
# a lot across MovieLens users but is ~1 for every live visitor (their likes
# are all from this session), so it would be a training/serving mismatch.

RETRIEVERS = ("ease", "als", "content", "popularity")


@dataclass
class ItemContext:
    """Per-movie facts as of a reference date (a fold's cutoff, or the end of
    the interaction data when serving)."""

    genres: np.ndarray  # (n_items, n_genres) 0/1 float32
    year: np.ndarray  # release year, NaN if unknown
    reference_year: int
    item_pop: np.ndarray  # likes before the reference date
    recent_pop: np.ndarray  # likes in the year before it

    def __post_init__(self) -> None:
        self.age = self.reference_year - self.year
        self.log_pop = np.log1p(self.item_pop)
        self.log_recent = np.log1p(self.recent_pop)
        self.share = self.recent_pop / (self.item_pop + 1.0)
        self.cold = (self.item_pop == 0).astype(np.float32)
        self.known_year = (~np.isnan(self.year)).astype(np.float32)
        self.year0 = np.nan_to_num(self.year, nan=0.0)


def ranks(scores: np.ndarray) -> np.ndarray:
    """1 = best, per row."""
    order = np.argsort(-scores, axis=1, kind="stable")
    out = np.empty_like(order)
    np.put_along_axis(out, order, np.arange(1, scores.shape[1] + 1)[None, :], axis=1)
    return out


def top_k(scores: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k best per row, best first."""
    k = min(k, scores.shape[1])
    part = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(scores, part, axis=1), axis=1, kind="stable")
    return np.take_along_axis(part, order, axis=1)


def pick_candidates(scores: dict[str, np.ndarray], per_source: dict[str, int]) -> np.ndarray:
    """Union of each retriever's top-n. Movies that cannot be recommended
    (already liked, or not released) must be -inf in every retriever."""
    excluded = np.isneginf(scores["ease"])
    pick = np.zeros(excluded.shape, dtype=bool)
    for name, n in per_source.items():
        np.put_along_axis(pick, top_k(scores[name], n), True, axis=1)
    return pick & ~excluded


def _relative(s: np.ndarray) -> np.ndarray:
    best = np.max(np.where(np.isfinite(s), s, -np.inf), axis=1, keepdims=True)
    return s / np.maximum(best, 1e-6)


def build(
    ctx: ItemContext, history: np.ndarray, scores: dict[str, np.ndarray], pick: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Features for every picked (user row, item) pair.

    history: (n_users, n_items) 0/1 likes; scores: retriever name -> (n_users,
    n_items) with already-liked movies at -inf; pick: candidate mask.
    Returns row ids, item ids and the (n_pairs, len(FEATURES)) matrix.
    """
    r, c = np.nonzero(pick)
    rk = {n: ranks(scores[n]) for n in ("ease", "als", "content")}
    rel = {n: _relative(scores[n]) for n in ("ease", "als")}

    n_likes = history.sum(axis=1)
    genre_dist = (history @ ctx.genres) / np.maximum(n_likes, 1)[:, None]
    mean_year = (history @ ctx.year0) / np.maximum(history @ ctx.known_year, 1)
    n_genres = np.maximum(ctx.genres[c].sum(axis=1), 1)

    x = np.column_stack([
        rel["ease"][r, c], rk["ease"][r, c],
        rel["als"][r, c], rk["als"][r, c],
        scores["content"][r, c], rk["content"][r, c],
        ctx.log_pop[c], ctx.log_recent[c], ctx.share[c], ctx.cold[c],
        ctx.age[c], np.abs(ctx.year[c] - mean_year[r]),
        np.einsum("ng,ng->n", genre_dist[r], ctx.genres[c]) / n_genres,
        np.log1p(n_likes[r]),
    ]).astype(np.float32)  # fmt: skip
    return r, c, x
