# neurohumanoid_RL — AAWR experiments

Simulation-first experiments with **Asymmetric Advantage Weighted Regression
(AAWR)** for active perception in robotics.

AAWR trains a deployable policy from partial observations while allowing the
critic to use privileged simulator state during training. The immediate goal of
this branch is to reproduce the reference simulation and then transfer the same
experimental protocol to two new robot embodiments:

0. reproduce the authors' simulated xArm experiment;
1. build an active-perception task for a LeRobot arm;
2. use the fixed Unitree G1 as a right-arm manipulator and train an initial
   active-perception policy.

## Upstream AAWR resources

- [Official AAWR implementation](https://github.com/penn-pal-lab/aawr) by the
  Penn Perception, Action, & Learning Group
- [Project page](https://penn-pal-lab.github.io/aawr/)
- [Paper: Real-World Reinforcement Learning of Active Perception Behaviors](https://arxiv.org/abs/2512.01188)
- [Local seminar slides](presentation/AAWR.pdf)

The upstream repository remains the source of truth for the algorithm. Any
copied or modified upstream code must retain its original license and record the
source commit.

## Roadmap

| Stage | Robot / environment | First result | Status |
| --- | --- | --- | --- |
| 0 | Authors' simulated xArm lift task | Reproduce BC, AWR, and AAWR learning curves | Not started |
| 1 | LeRobot arm | Learn to reveal an occluded target before reaching/grasping | Planned |
| 2 | Fixed Unitree G1, right arm only | Learn wrist-camera viewpoint search with the 7-DoF arm | Planned |

The stages are intentionally sequential. Stage 0 establishes a known-good AAWR
pipeline and baseline numbers before robot- or simulator-specific changes are
introduced.

### 0 — Reproduce the official simulation

Start from the official toy xArm setup and its documented training entrypoint.
The reproduction should:

- pin the AAWR and `gym-xarm` source revisions;
- generate and version the dataset manifest, not large generated datasets;
- run BC, unprivileged AWR, and AAWR with the same data and evaluation budget;
- use at least three seeds for the comparison run;
- save resolved configs, scalar metrics, checkpoints, and rollout videos;
- report success rate, return, episode length, and variation across seeds;
- test full, noisy, and zeroed privileged state as the first ablation.

Stage 0 is complete when a clean checkout can reproduce the experiment and the
AAWR result is compared with BC/AWR in a short report. Exact agreement with the
paper is not required, but deviations must be recorded.

See [`experiments/00_official_sim/`](experiments/00_official_sim/) for the
experiment card.

### 1 — LeRobot arm

Create a small manipulation scene in which the target is initially occluded.
The first policy should learn to move the camera, arm, or an occluding object to
obtain a useful view before attempting a reach or grasp.

The actor may use only deployable observations such as camera frames, joint
state, and observation/action history. The AAWR critic may additionally use
simulator-only target pose, occluder pose, contacts, and task phase. BC and
unprivileged AWR remain mandatory baselines.

The exact LeRobot-compatible arm and simulator are deliberately not fixed yet;
they should be selected and pinned in the experiment card before implementation.

See [`experiments/01_lerobot/`](experiments/01_lerobot/) for the initial design.

### 2 — Unitree G1

Use G1 as a stationary manipulator for the first iteration. Fix the pelvis/base,
hold the legs, waist, left arm, and other inactive joints in a nominal pose, and
allow AAWR to control only the seven joints of the right arm available in the
current simulation asset: three shoulder joints, elbow, and three wrist joints.
This removes balance and locomotion from the first experiment while preserving
the G1 kinematics and workspace.

Mount a simulated wrist camera on the right arm and place the target outside its
initial view or behind an occluder. The policy must move the arm to obtain an
informative view, reveal/localize the target, and then reach it or hand control
to a downstream manipulation policy. The actor receives only wrist-camera
observations, right-arm joint state, and history; the privileged AAWR critic may
also receive target/occluder poses, visibility, and contact state.

This `G1-v0` task intentionally treats G1 as a 7-DoF manipulator rather than as
a complete humanoid. Once it works, increase complexity in stages: unlock the
waist, replace the fixed base with a standing controller, and only then permit
small whole-body viewpoint changes or steps. Before real-robot transfer, pin the
hardware variant: standard G1 arms have five DoF, while the extra wrist axes are
configuration-dependent.

See [`experiments/02_unitree_g1/`](experiments/02_unitree_g1/) for the initial
design.

## Repository layout

```text
.
├── README.md
├── presentation/
│   └── AAWR.pdf
└── experiments/
    ├── README.md
    ├── 00_official_sim/
    ├── 01_lerobot/
    └── 02_unitree_g1/
```

As implementation grows, each experiment directory should own its configs,
scripts, environment adapters, and report. Shared algorithm code should live in
a top-level `src/` package only after the Stage 0 integration makes its interface
clear.

## Experiment rules

- Keep robot/simulator integration separate from AAWR algorithm changes.
- Every result must identify code revision, dataset, seed, and resolved config.
- Compare methods with identical data and evaluation budgets.
- Do not commit raw datasets, generated videos, checkpoints, or online logger
  caches; store manifests and retrieval instructions instead.
- A result is not complete until it has a headless smoke-test command and a
  short written conclusion.

## Current state

This branch currently contains planning documentation and the AAWR seminar
slides. No upstream code, simulator environment, or reproduced result has been
added yet.
