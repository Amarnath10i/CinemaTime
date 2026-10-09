"""Paths and the evaluation protocol, in one place."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ML = Path(__file__).resolve().parents[1]
REPO = ML.parent


@dataclass(frozen=True)
class Paths:
    raw: Path = ML / "data" / "raw" / "ml-32m"
    cache: Path = ML / "data" / "cache"
    reports: Path = ML / "reports"
    catalog: Path = REPO / "backend" / "movies.pkl"
    content_index: Path = REPO / "backend" / "movies.index"
    export: Path = REPO / "backend" / "recsys"


@dataclass(frozen=True)
class Protocol:
    """Temporal evaluation: models only ever see the past.

    Hyperparameters and the ranker are fitted on the validation fold
    (train < valid_start, evaluate [valid_start, test_start)); the final numbers
    come from the test fold (train < test_start, evaluate [test_start, end)).
    """

    valid_start: pd.Timestamp = pd.Timestamp("2021-10-12")
    test_start: pd.Timestamp = pd.Timestamp("2022-10-12")
    end: pd.Timestamp = pd.Timestamp("2023-10-14")
    positive_rating: float = 4.0  # a "like": 4 stars or more
    min_history: int = 5  # evaluated users need this many past likes
    ks: tuple[int, ...] = (10, 20, 50)


@dataclass(frozen=True)
class Settings:
    paths: Paths = field(default_factory=Paths)
    protocol: Protocol = field(default_factory=Protocol)
    seed: int = 42


settings = Settings()
