#!/usr/bin/env python3
"""Summarize completed Stage 0 evaluation CSVs without changing artifacts."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "stage0" / "main"


def load_run(path: Path) -> list[dict[str, float]]:
    with path.open(newline="") as file:
        return [{key: float(value) for key, value in row.items()} for row in csv.DictReader(file)]


def main() -> None:
    completed: dict[str, list[dict[str, float]]] = {}
    print("| Method | Seed | Final success | Best success | Last-5 mean | Final length |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for method in ("bc", "awr", "aawr"):
        completed[method] = []
        for seed in (41, 42, 43):
            path = RESULTS / method / str(seed) / "eval.csv"
            if not path.exists():
                continue
            rows = load_run(path)
            final = rows[-1]
            completed[method].append(final)
            last_five = statistics.mean(row["episode_success"] for row in rows[-5:])
            best = max(row["episode_success"] for row in rows)
            print(
                f"| {method.upper()} | {seed} | {final['episode_success']:.3f} | "
                f"{best:.3f} | {last_five:.3f} | {final['episode_length']:.3f} |"
            )

    print("\nFinal-success aggregate over completed seeds:")
    for method in ("bc", "awr", "aawr"):
        values = [row["episode_success"] for row in completed[method]]
        if values:
            spread = statistics.stdev(values) if len(values) > 1 else 0.0
            print(f"- {method.upper()}: {statistics.mean(values):.3f} ± {spread:.3f} (n={len(values)})")


if __name__ == "__main__":
    main()
