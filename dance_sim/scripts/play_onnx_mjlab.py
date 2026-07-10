#!/usr/bin/env python3
"""Play a deployed Unitree ONNX policy in unitree_rl_mjlab/MuJoCo.

This is intentionally local-only glue code for /home/al/humanoid/dance_sim.
It reuses the upstream mjlab task/env and feeds obs["actor"] into the exported
deploy ONNX policy.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch


def _add_repo_to_path(repo: Path) -> None:
    sys.path.insert(0, str(repo))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default="/home/al/humanoid/dance_sim/external/unitree_rl_mjlab",
        help="Path to cloned unitree_rl_mjlab repo.",
    )
    parser.add_argument(
        "--task",
        default="Unitree-G1-Tracking-No-State-Estimation",
    )
    parser.add_argument(
        "--motion-file",
        default="/home/al/humanoid/dance_sim/experiments/full_20p50_to_end.npz",
    )
    parser.add_argument(
        "--policy",
        default="/home/al/humanoid/dance_sim/assets/policies/mimic/dance1_subject2/exported/policy.onnx",
    )
    parser.add_argument("--num-envs", type=int, default=1)
    parser.add_argument("--device", default=None)
    parser.add_argument("--viewer", choices=["auto", "native", "viser", "none"], default="native")
    parser.add_argument("--steps", type=int, default=0, help="Headless steps for --viewer none; 0 means run forever in viewer.")
    parser.add_argument("--no-terminations", action="store_true", default=True)
    parser.add_argument("--ort-provider", choices=["auto", "cuda", "cpu"], default="auto")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    _add_repo_to_path(repo)

    import mjlab.tasks  # noqa: F401
    import src.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg
    from mjlab.tasks.tracking.mdp import MotionCommandCfg
    from mjlab.viewer import NativeMujocoViewer, ViserPlayViewer

    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")

    env_cfg = load_env_cfg(args.task, play=True)
    agent_cfg = load_rl_cfg(args.task)
    env_cfg.scene.num_envs = args.num_envs
    if args.no_terminations:
        env_cfg.terminations = {}

    motion_cmd = env_cfg.commands["motion"]
    assert isinstance(motion_cmd, MotionCommandCfg)
    motion_cmd.motion_file = args.motion_file

    available = ort.get_available_providers()
    if args.ort_provider == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif args.ort_provider == "cpu":
        providers = ["CPUExecutionProvider"]
    else:
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if "CUDAExecutionProvider" in available and torch.cuda.is_available()
            else ["CPUExecutionProvider"]
        )

    session = ort.InferenceSession(args.policy, providers=providers)
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    print(f"[INFO] Torch device: {device}")
    print(f"[INFO] ONNX providers: {session.get_providers()}")
    print(f"[INFO] Motion: {args.motion_file}")
    print(f"[INFO] Policy: {args.policy}")

    env = ManagerBasedRlEnv(cfg=env_cfg, device=device, render_mode=None)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

    class OnnxPolicy:
        def __call__(self, obs) -> torch.Tensor:
            actor = obs["actor"] if hasattr(obs, "__getitem__") else obs
            actor_np = actor.detach().cpu().numpy().astype(np.float32)
            actions = session.run([output_name], {input_name: actor_np})[0]
            return torch.from_numpy(actions).to(actor.device)

    policy = OnnxPolicy()

    if args.viewer == "none":
        obs = env.get_observations()
        steps = args.steps or 500
        for step in range(steps):
            obs, _, _, _ = env.step(policy(obs))
        print(f"[INFO] Headless ONNX play stepped {steps} frames OK")
        env.close()
        return

    viewer = args.viewer
    if viewer == "auto":
        viewer = "native" if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) else "viser"

    if viewer == "native":
        NativeMujocoViewer(env, policy).run()
    else:
        ViserPlayViewer(env, policy).run()
    env.close()


if __name__ == "__main__":
    main()
