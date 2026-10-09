"""Shared helpers: data loading once per process, report writing, best parameters."""

from __future__ import annotations

import json
from functools import cache

from cinemaml.config import settings
from cinemaml.data import Fold, Items, load_items, load_likes, make_fold

BEST = settings.paths.reports / "best_params.json"


@cache
def items() -> Items:
    return load_items()


@cache
def fold(name: str) -> Fold:
    p = settings.protocol
    likes = load_likes(items())
    if name == "valid":
        return make_fold(likes, len(items()), p.valid_start, p.test_start, "valid")
    return make_fold(likes, len(items()), p.test_start, p.end, "test")


def write_report(name: str, text: str) -> None:
    settings.paths.reports.mkdir(parents=True, exist_ok=True)
    (settings.paths.reports / f"{name}.md").write_text(text, encoding="utf-8")


def best_params() -> dict:
    return json.loads(BEST.read_text()) if BEST.exists() else {}
