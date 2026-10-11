"""`uv run cinemaml <experiment>` runs one experiment and prints its report."""

from __future__ import annotations

import argparse
import importlib
import logging

EXPERIMENTS = {
    "tune": "Hyperparameter selection on the validation fold",
    "compare": "Every model on the test fold, with bootstrap intervals",
    "coldstart": "Content-to-collaborative mapping for movies nobody has rated yet",
    "ablation": "Retrain the ranker without each feature group",
    "diversity": "MMR re-ranking: accuracy vs diversity trade-off",
    "groups": "Group recommendation strategies on real users",
    "export": "Replay the served engine, then write backend/recsys/artifacts/",
}


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("faiss").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(prog="cinemaml")
    parser.add_argument("experiment", choices=EXPERIMENTS)
    args = parser.parse_args(argv)
    module = importlib.import_module(f"cinemaml.experiments.{args.experiment}")
    print(module.run())


if __name__ == "__main__":
    main()
