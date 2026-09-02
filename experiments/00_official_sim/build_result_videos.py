#!/usr/bin/env python3
"""Build compact labeled Stage 0 rollout videos from completed seed-41 runs."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AAWR_LOGS = ROOT / ".external" / "aawr" / "logs" / "gymnasium_xarm_lift"
RESULTS = ROOT / "results" / "stage0" / "main"
OUTPUT = ROOT / "results" / "stage0" / "videos"
SEED = 41

METHODS = (
    ("BC", "bc", "pixels", "#4C9AFF"),
    ("AWR", "awr", "pixels", "#FFAB00"),
    ("AAWR", "aawr", "all", "#36B37E"),
)


def final_metrics(method: str) -> dict[str, float]:
    path = RESULTS / method / str(SEED) / "eval.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing completed result: {path}")
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    return {key: float(value) for key, value in rows[-1].items()}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    labeled: list[Path] = []

    for display, method, modality, color in METHODS:
        metrics = final_metrics(method)
        step = int(metrics["env_step"])
        source = (
            AAWR_LOGS
            / modality
            / f"stage0_main_{method}"
            / str(SEED)
            / "eval_video"
            / f"{step}.mp4"
        )
        if not source.exists():
            raise FileNotFoundError(f"Missing rollout video: {source}")

        target = OUTPUT / f"{method}_seed{SEED}_final.mp4"
        label = (
            f"{display}  |  success {metrics['episode_success']:.3f}  |  "
            f"steps {metrics['episode_length']:.1f}"
        )
        filter_graph = (
            "scale=320:320:flags=lanczos,"
            "pad=320:372:0:52:color=#101214,"
            f"drawtext=text='{label}':fontcolor={color}:fontsize=16:"
            "x=(w-text_w)/2:y=18"
        )
        run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vf",
                filter_graph,
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                "20",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(target),
            ]
        )
        labeled.append(target)

    comparison = OUTPUT / f"comparison_seed{SEED}_final.mp4"
    run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(labeled[0]),
            "-i",
            str(labeled[1]),
            "-i",
            str(labeled[2]),
            "-filter_complex",
            "[0:v][1:v][2:v]hstack=inputs=3:shortest=1[v]",
            "-map",
            "[v]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(comparison),
        ]
    )

    for path in (*labeled, comparison):
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size / 1024:.1f} KiB")


if __name__ == "__main__":
    main()
