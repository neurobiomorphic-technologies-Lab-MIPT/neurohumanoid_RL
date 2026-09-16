#!/usr/bin/env python3
"""Run Gymnasium checks and scripted SO-101 lift rollouts."""

from __future__ import annotations

import argparse
from pathlib import Path

import gymnasium as gym
from gymnasium.utils.env_checker import check_env
import gym_so101_aawr  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()

    check_target = gym.make(
        "gym_so101_aawr/SO101Lift-v0", scene_path=args.scene, render_mode="rgb_array"
    ).unwrapped
    check_env(check_target, skip_render_check=False)
    check_target.close()

    completed = 0
    env = gym.make("gym_so101_aawr/SO101Lift-v0", scene_path=args.scene, render_mode="rgb_array")
    try:
        for episode in range(args.episodes):
            _, _ = env.reset(seed=41 + episode)
            for _ in range(3):
                action = env.action_space.sample()
                observation, _, terminated, truncated, _ = env.step(action)
                assert observation in env.observation_space
                if terminated or truncated:
                    break
            completed += 1
    finally:
        env.close()
    print(f"gymnasium_rollouts={completed}/{args.episodes}")


if __name__ == "__main__":
    main()
