#!/usr/bin/env python3
"""Convert public SO-101 teleop trajectories into AAWR lift demonstrations."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
import pandas as pd
import gym_so101_aawr  # noqa: F401


JOINT_NAMES = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
OFFSETS = np.array(
    [(dx, dy) for dx in (0.0, 0.01, -0.01) for dy in (0.02, 0.01, 0.03, 0.0, 0.04)],
    dtype=np.float64,
)


def model_ids(model: mujoco.MjModel) -> dict[str, np.ndarray | int]:
    joint_ids = np.array(
        [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in JOINT_NAMES]
    )
    block_joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "block")
    return {
        "qpos": model.jnt_qposadr[joint_ids],
        "dof": model.jnt_dofadr[joint_ids],
        "act": np.array(
            [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name) for name in JOINT_NAMES]
        ),
        "ee": mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "gripperframe"),
        "block_qpos": int(model.jnt_qposadr[block_joint]),
    }


def replay(
    model: mujoco.MjModel,
    ids: dict[str, np.ndarray | int],
    actions: np.ndarray,
    states: np.ndarray,
    start: int,
    end: int,
    cube_xy: np.ndarray,
) -> tuple[float, np.ndarray]:
    data = mujoco.MjData(model)
    data.qpos[ids["qpos"]] = states[start, :6]
    data.qvel[ids["dof"]] = states[start, 6:12]
    data.ctrl[ids["act"]] = actions[start]
    block_qpos = ids["block_qpos"]
    data.qpos[block_qpos : block_qpos + 7] = [cube_xy[0], cube_xy[1], 0.0125, 1, 0, 0, 0]
    mujoco.mj_forward(model, data)
    max_height = 0.0
    for index in range(start, end):
        data.ctrl[ids["act"]] = actions[index]
        for _ in range(18):
            mujoco.mj_step(model, data)
        max_height = max(max_height, float(data.qpos[block_qpos + 2]))
    return max_height, data.site_xpos[ids["ee"]].copy()


def build_profiles(dataframe: pd.DataFrame, scene: Path) -> dict[str, np.ndarray]:
    model = mujoco.MjModel.from_xml_path(str(scene))
    model.opt.timestep = 1.0 / 360.0
    ids = model_ids(model)
    profiles: dict[str, list[np.ndarray | int]] = {
        "qpos": [], "qvel": [], "ctrl": [], "cube_xy": [], "targets": [], "lengths": [], "source_episode": []
    }
    for episode_index, episode in dataframe.groupby("episode_index", sort=True):
        actions = np.stack(episode["action"].to_numpy()).astype(np.float32)
        states = np.stack(episode["observation.state"].to_numpy()).astype(np.float32)
        gripper = actions[:, 5]
        close_candidates = np.flatnonzero((gripper < 0.1) & (np.maximum.accumulate(gripper) > 0.6))
        if len(close_candidates) == 0:
            continue
        close_index = int(close_candidates[0])
        start = max(0, close_index - 25)
        end = min(len(actions), close_index + 100)
        _, grasp_site = replay(model, ids, actions, states, start, close_index + 1, np.array([2.0, 2.0]))

        best_height = -np.inf
        best_xy = None
        for offset in OFFSETS:
            cube_xy = grasp_site[:2] + offset
            height, _ = replay(model, ids, actions, states, start, end, cube_xy)
            if height > best_height:
                best_height, best_xy = height, cube_xy.copy()
            if height >= 0.08:
                break
        if best_height < 0.08:
            continue
        targets = actions[start:end]
        profiles["qpos"].append(states[start, :6])
        profiles["qvel"].append(states[start, 6:12])
        profiles["ctrl"].append(actions[start])
        profiles["cube_xy"].append(best_xy)
        profiles["targets"].append(targets)
        profiles["lengths"].append(len(targets))
        profiles["source_episode"].append(int(episode_index))

    if not profiles["qpos"]:
        raise RuntimeError("No successful replay profiles could be recovered")
    max_length = max(profiles["lengths"])
    padded_targets = np.zeros((len(profiles["targets"]), max_length, 6), dtype=np.float32)
    for index, targets in enumerate(profiles["targets"]):
        padded_targets[index, : len(targets)] = targets
    return {
        "qpos": np.asarray(profiles["qpos"], dtype=np.float32),
        "qvel": np.asarray(profiles["qvel"], dtype=np.float32),
        "ctrl": np.asarray(profiles["ctrl"], dtype=np.float32),
        # Contact can be sensitive at the jaw boundary; do not quantize poses.
        "cube_xy": np.asarray(profiles["cube_xy"], dtype=np.float64),
        "targets": padded_targets,
        "lengths": np.asarray(profiles["lengths"], dtype=np.int32),
        "source_episode": np.asarray(profiles["source_episode"], dtype=np.int32),
    }


def collect_buffer(scene: Path, profiles_path: Path, repeats: int) -> tuple[dict, dict]:
    profiles = np.load(profiles_path, allow_pickle=False)
    env = gym.make(
        "gym_so101_aawr/SO101Lift-v0",
        scene_path=scene,
        reset_profiles_path=profiles_path,
        render_mode="rgb_array",
    )
    records: dict[str, list] = {
        "observations": [], "next_observations": [], "actions": [], "rewards": [],
        "terminated": [], "dones": [], "masks": [],
    }
    successes = 0
    try:
        for _ in range(repeats):
            for profile_index in range(len(profiles["qpos"])):
                observation, _ = env.reset(options={"profile_index": profile_index})
                success = False
                for target in profiles["targets"][profile_index, : profiles["lengths"][profile_index]]:
                    raw = env.unwrapped
                    action = np.clip(
                        (target - raw.data.ctrl[raw.actuator_ids]) / raw.action_scale, -1, 1
                    ).astype(np.float32)
                    next_observation, reward, terminated, truncated, info = env.step(action)
                    done = terminated or truncated
                    records["observations"].append(observation)
                    records["next_observations"].append(next_observation)
                    records["actions"].append(action)
                    records["rewards"].append(reward)
                    records["terminated"].append(terminated)
                    records["dones"].append(done)
                    records["masks"].append(0.0 if terminated else 1.0)
                    observation = next_observation
                    if done:
                        success = bool(info["is_success"])
                        break
                successes += int(success)
                if not success:
                    raise RuntimeError(f"Recovered profile {profile_index} failed during buffer collection")
    finally:
        env.close()

    def stack_observation(key: str) -> dict[str, np.ndarray]:
        return {
            name: np.stack([item[name] for item in records[key]])
            for name in ("rgb", "state")
        }

    buffer = {
        "observations": stack_observation("observations"),
        "next_observations": stack_observation("next_observations"),
        "actions": np.stack(records["actions"]).astype(np.float32),
        "rewards": np.asarray(records["rewards"], dtype=np.float32),
        "terminated": np.asarray(records["terminated"], dtype=bool),
        "dones": np.asarray(records["dones"], dtype=bool),
        "masks": np.asarray(records["masks"], dtype=np.float32),
    }
    metadata = {
        "profiles": int(len(profiles["qpos"])),
        "episodes": int(len(profiles["qpos"]) * repeats),
        "transitions": int(len(buffer["actions"])),
        "successes": int(successes),
        "source_episodes": profiles["source_episode"].tolist(),
    }
    buffer["metadata"] = metadata
    return buffer, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    profiles_path = args.output / "reset_profiles.npz"
    buffer_path = args.output / "buffer.pkl"
    if profiles_path.exists() or buffer_path.exists():
        raise SystemExit(f"Refusing to overwrite dataset files in {args.output}")

    dataframe = pd.read_parquet(args.reference)
    profiles = build_profiles(dataframe, args.scene.resolve())
    np.savez_compressed(profiles_path, **profiles)
    buffer, metadata = collect_buffer(args.scene.resolve(), profiles_path, args.repeats)
    with buffer_path.open("wb") as stream:
        pickle.dump(buffer, stream)
    metadata.update(
        {
            "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
            "buffer_sha256": hashlib.sha256(buffer_path.read_bytes()).hexdigest(),
        }
    )
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
