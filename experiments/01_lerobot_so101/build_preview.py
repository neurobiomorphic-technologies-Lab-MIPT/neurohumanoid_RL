#!/usr/bin/env python3
"""Render a compact, explicitly labeled expert-data preview GIF."""

from __future__ import annotations

import argparse
from pathlib import Path

import gymnasium as gym
import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw
import gym_so101_aawr  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=int, default=0)
    args = parser.parse_args()

    profiles = np.load(args.profiles, allow_pickle=False)
    env = gym.make(
        "gym_so101_aawr/SO101Lift-v0",
        scene_path=args.scene,
        reset_profiles_path=args.profiles,
        render_mode="rgb_array",
    )
    frames = []
    try:
        observation, _ = env.reset(options={"profile_index": args.profile})
        targets = profiles["targets"][args.profile, : profiles["lengths"][args.profile]]
        for step, target in enumerate(targets):
            raw = env.unwrapped
            action = np.clip((target - raw.data.ctrl[raw.actuator_ids]) / raw.action_scale, -1, 1)
            observation, _, terminated, truncated, info = env.step(action)
            if step % 2 == 0 or terminated:
                image = Image.fromarray(observation["rgb"]).resize((336, 336), Image.Resampling.NEAREST)
                draw = ImageDraw.Draw(image)
                draw.rectangle((0, 0, 336, 36), fill=(8, 12, 18))
                draw.text((9, 5), "EXPERT DATA  |  SO-101 LIFT", fill=(255, 255, 255))
                draw.text((9, 20), f"cube height {info['block_height'] * 100:.1f} cm", fill=(130, 230, 160))
                frames.append(np.asarray(image))
            if terminated or truncated:
                break
    finally:
        env.close()

    if not info["is_success"]:
        raise SystemExit("Selected expert profile did not lift the cube")
    frames.extend([frames[-1]] * 8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(args.output, frames, duration=0.10, loop=0, palettesize=128)
    print(f"wrote {args.output} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
