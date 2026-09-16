# Stage 1 — AAWR on the LeroBot SO-101

This stage moves the validated AAWR pipeline from the upstream xArm toy task to
the six-actuator SO-101 used by LeRobot. It is simulation-only: no serial port is
opened and the physical arm is never commanded.

## Current scope

- MuJoCo SO-101 `simple_pick` scene from
  [SO-101 SimStudio](https://github.com/rocPAI-Forge/so101-simstudio), derived
  from [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100).
- Actor input: one 84×84 front RGB image.
- AAWR privileged critic: 34-D simulator state (joints, velocities, end
  effector, cube pose/velocity, and actuator targets).
- Action: six normalized joint deltas matching the SO-101 joint ordering.
- Success: lift the cube centre to at least 8 cm.

The first curriculum deliberately starts 1.25 seconds before gripper closure.
It proves the SO-101/AAWR integration and grasp dynamics, but does **not** yet
solve reaching from the fixed home pose. The next curriculum must progressively
move reset earlier in the expert trajectories before any sim-to-real claim.

![Validated SO-101 expert lift](assets/expert_lift.gif)

This preview is a replayed expert trajectory, not a learned-policy result. The
10k AAWR run reached 50% success at its best evaluation checkpoints and ended
at 30%; the full curve and limitations are recorded in [`report.md`](report.md).

### Learned-policy comparison

[Watch the full evaluation reel](assets/all_eval_checkpoints.mp4) (1:45, 4.7 MB).
It uses the first recorded episode at five fixed checkpoints for each method,
including zero-success checkpoints and regressions. The caption on every clip
reports the success rate over its complete ten-episode evaluation batch.

The historical recordings are intrinsically 84×84 because the first logger
reused the actor observation. They are enlarged for viewing but contain no
invented detail. New runs use a separate 384×384 video renderer and save policy
checkpoints, while the actor input remains 84×84.

## Reproduce

```bash
./experiments/01_lerobot_so101/bootstrap.sh
./experiments/01_lerobot_so101/generate_demos.sh
./experiments/01_lerobot_so101/run_experiment.sh aawr 41
```

The public 50-episode SimStudio teleoperation parquet is only 2.5 MB; its large
camera videos are not downloaded. The converter infers the jaw-centred cube
pose, replays every candidate in MuJoCo, rejects failures, and generates a local
AAWR buffer. The measured dataset identity is in
[`dataset-manifest.yaml`](dataset-manifest.yaml).

Generated datasets, logs, models and videos are ignored by Git. External
logging and WandB are disabled.

## Sim-to-real boundary

The local physical SO-101 has the same ordered six joint channels and two
640×480 cameras. Those files were inspected only to establish the interface;
real recordings and calibration values are not copied into this repository.
Before hardware deployment, add camera matching/domain randomization, action
rate and joint-limit safety, an emergency stop, and shadow-mode evaluation.

The intended transfer sequence is:

1. match the real camera pose, crop, resolution, joint convention, control rate,
   limits and calibration in MuJoCo;
2. randomize lighting, textures, camera extrinsics, cube pose, latency, motor
   strength, friction and observation noise during training;
3. export only the actor (RGB to six bounded joint deltas), then replay it first
   against recorded observations and in a no-motion shadow mode;
4. test on hardware at reduced speed with workspace clamps, per-step delta
   limits, gripper limits and a physical emergency stop;
5. collect guarded real rollouts, mix successful real data into the offline
   buffer, and fine-tune with progressively less simulation data.

The current near-grasp curriculum is not ready for step 3: reaching from home,
multi-camera robustness, safety wrapping and checkpoint selection must come
first.

The detailed implementation sequence, quantitative promotion gates, experiment
matrix, video standard, and guarded hardware protocol are in the
[`simulation-to-real roadmap`](roadmap_sim_to_real.md).

Isaac Lab is not required for this first stage. The MuJoCo path uses about 31 MB
of external simulator sources. If contact fidelity or large-scale domain
randomization later requires Isaac, reserve at least 60–80 GB of free disk
(preferably roughly 100 GB including caches and experiment outputs).
