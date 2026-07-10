# neurohumanoid_RL — dance_train

Training/simulation branch for Unitree G1 dance work.

This branch is separate from `dance_deploy`:

- `dance_deploy` keeps the robot-side deploy package.
- `dance_train` keeps the MuJoCo/mjlab training and local simulation workspace.

## Contents

- `unitree_rl_mjlab/` — upstream Unitree RL Mjlab source used for training/play.
- `dance_sim/` — local dance workspace:
  - `assets/` — copied deploy policies/motions/configs used for analysis and ONNX play.
  - `experiments/` — generated motion cuts, including `full_20p50_to_end.npz`.
  - `scripts/` — local motion utilities and ONNX MuJoCo player.
  - `notes/` — local reasoning notes.
  - `run_*.sh` — local helper launch scripts.

Not included:

- `.venv/`
- `logs/`
- `wandb/`
- training checkpoints such as `*.pt`
- Python caches / egg-info / nested `.git`

## Environment

From the repo root:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -e unitree_rl_mjlab
```

For the local setup we also used:

```bash
uv pip install --python .venv/bin/python onnxruntime-gpu scipy
```

Important note from the laptop test: `nvidia-smi` saw the RTX 3080, but CUDA
runtime returned `cuInit(0)=999`, so local MuJoCo/Warp ran on CPU until the
driver/runtime state is fixed.

## Train imitation policy

Example G1 tracking training command:

```bash
cd unitree_rl_mjlab
../.venv/bin/python scripts/train.py Unitree-G1-Tracking-No-State-Estimation \
  --motion-file ../dance_sim/assets/policies/mimic/dance1_subject2/params/dance1_subject2.npz \
  --env.scene.num-envs=4096
```

Use a smaller `num-envs` first if debugging locally.

## Play trained `.pt` checkpoint in MuJoCo

```bash
cd unitree_rl_mjlab
../.venv/bin/python scripts/play.py Unitree-G1-Tracking-No-State-Estimation \
  --motion-file ../dance_sim/assets/policies/mimic/dance1_subject2/params/dance1_subject2.npz \
  --checkpoint-file logs/rsl_rl/g1_tracking/<run>/model_<iter>.pt \
  --num-envs 1 \
  --device cuda:0
```

If CUDA is broken on the machine, use `--device cpu`.

## Play deployed ONNX policy against MuJoCo env

This uses the local glue script that feeds `obs["actor"]` into the exported
deploy ONNX policy.

Headless smoke test:

```bash
cd dance_sim
./run_onnx_headless_check.sh 200 cpu
```

Native viewer:

```bash
cd dance_sim
./run_onnx_play_20p50_to_end.sh cpu
```

The default motion here is:

```text
dance_sim/experiments/full_20p50_to_end.npz
```

That file is the full dance cropped from `20.50s` to the end.
