# SO-101 simulation-to-real roadmap

## North-star task

Train a camera-driven SO-101 policy that starts from a safe home pose, finds a
randomized cube, grasps it, lifts it, holds it, transports it into a marked
target zone, releases it, and retreats without violating safety limits. The
deployed actor may use only observations available on the real robot. Simulator
state is restricted to the AAWR critic, reward computation, validation, and
diagnostics.

One successful episode must complete every phase:

1. **reach** — bring the open gripper to a collision-free pre-grasp pose;
2. **grasp** — close around the cube without pushing it out of the workspace;
3. **lift** — raise the cube centre above 10 cm;
4. **hold** — keep it above 10 cm for at least one second;
5. **transport** — move it above a randomized target zone;
6. **place** — lower it into the zone and release it;
7. **settle** — keep the cube in the zone for one second and retreat.

Success is evaluated only after `settle`; videos continue for two seconds after
success. Grasp or first contact alone is never success.

## Non-negotiable experiment contract

- Actor input: real-deployable RGB, six joint positions, previous action, and a
  short observation/action history. No cube pose, task phase, contact force, or
  simulator segmentation may leak into the actor.
- AAWR critic input: actor observations plus cube/target pose, contacts,
  velocities, visibility, task phase, and randomized simulator parameters.
- Action: bounded six-joint target increments at the measured real control rate.
- Every run records code/data revisions, resolved config, seed, checkpoints,
  per-phase metrics, safety violations, and all evaluation episodes.
- BC, AWR, and AAWR use the same demonstrations, augmentations, network budget,
  training steps, evaluation starts, and seeds.
- Hyperparameters are selected on validation layouts; the final test layouts
  remain untouched until the comparison is frozen.

## Work packages

### WP0 — Make evaluation trustworthy

- Save final, periodic, offline-final, and best-validation checkpoints.
- Render evaluation at 384×384 or higher independently of the 84×84 policy
  input; retain the unmodified policy frame for debugging.
- Record all evaluation episodes, including failures, with seed, checkpoint,
  phase, cube height, and success overlaid.
- Add deterministic reset tests and a replay test that reproduces actions,
  rewards, termination, and final object pose.
- Add a failure taxonomy: no reach, bad approach, push-away, missed grasp,
  dropped object, bad placement, timeout, collision, and safety intervention.

**Gate:** repeated evaluation of one checkpoint produces identical metrics;
every aggregate number can be traced to its complete set of videos.

### WP1 — Replace lift-v0 with full pick-place-v1

- Implement an explicit seven-phase task state machine matching the north-star
  task.
- Separate `terminated` (successful settled placement) from `truncated`
  (timeout); never terminate on initial lift.
- Log phase completion and time-to-phase in addition to episode success.
- Use sparse terminal success for headline results. Any shaped training reward
  is versioned and audited for exploits against the sparse evaluator.
- Add table, cube, target-zone, self-collision, floor-contact, workspace, joint,
  velocity, and action-delta checks.
- Extend the post-success rollout so videos prove hold, release, settling, and
  retreat.

**Gate:** scripted expert completes at least 99/100 randomized nominal episodes,
and deliberately broken trajectories fail the correct phase-specific tests.

### WP2 — Build a progressive curriculum

| Level | Reset and task | Promotion criterion |
| --- | --- | --- |
| C0 | Current near-grasp lift | Integration only; never used for transfer claims |
| C1 | Random pre-grasp reach, grasp, lift, hold | ≥90% over 100 episodes |
| C2 | Fixed home pose, randomized cube, lift and hold | ≥85% over 200 episodes |
| C3 | Home-to-pick-to-place, fixed camera/target family | ≥80% over 200 episodes |
| C4 | Randomized cube, target, camera and dynamics | ≥80% over 500 episodes |
| C5 | Partial occlusion requiring active viewpoint change | ≥75% over 500 episodes |

Promotion is based on held-out resets and the median of at least three seeds,
not on one best checkpoint. Mix earlier levels into later training so the policy
does not forget grasping while learning transport and placement.

### WP3 — Produce strong, validated demonstrations

- Implement a phase-aware Cartesian expert using IK, collision checks, gripper
  timing, and retry/recovery logic.
- Generate successful demonstrations across all curriculum levels and preserve
  failed attempts in a separate diagnostic split.
- Validate every stored transition by physics replay; reject pose drift,
  discontinuous actions, unsafe joint targets, and mislabeled success.
- Create train/validation/test splits by cube position, target position, camera
  perturbation, and random seed—not by adjacent frames from the same episode.
- Track dataset manifests, distributions, checksums, and success by curriculum
  level. Do not commit raw datasets.

**Initial target:** at least 1,000 validated successful pick-place episodes with
balanced coverage of the workspace before the final algorithm comparison.

### WP4 — Train and compare algorithms honestly

Run BC, AWR, and AAWR first on C1–C3, then on C4–C5. Use at least five seeds for
the frozen comparison. Report median, interquartile range, and worst seed for:

- full task success and every phase success;
- time to grasp, lift, and placement;
- drop, collision, timeout, and safety-intervention rates;
- nominal, randomized, held-out-layout, and stress-test performance;
- best-validation checkpoint and final checkpoint, both clearly identified.

Required AAWR ablations:

- full privileged critic state;
- no privileged state (matched AWR boundary);
- zeroed or noisy privileged state;
- object pose only, contact only, and visibility only;
- fixed versus scheduled AAWR filtering/expectile settings.

Do not tune AAWR on the test seeds merely to make it win. If BC remains better,
that is the result; active perception C5 is the task where privileged training
has the clearest opportunity to add value.

### WP5 — Calibrate simulation from the real setup

Measure rather than guess:

- joint zero offsets, limits, direction conventions, repeatability, backlash,
  maximum safe increments, and achieved control frequency;
- camera intrinsics, distortion, exposure range, pose relative to the base, crop,
  image delay, and dropped-frame behavior;
- table plane, workspace bounds, cube mass/size, gripper geometry, friction,
  closing time, and command-to-motion latency.

Create one versioned calibration file containing safe, non-identifying numeric
parameters. Add a real-to-sim pose sanity tool: given one real joint snapshot,
render the simulated arm and compare projected keypoints. Calibration data must
never silently alter an existing experiment.

### WP6 — Systematic robustness and domain randomization

Randomize only around measured ranges, then widen them in stress tests:

- camera extrinsics/intrinsics, crop, latency, blur, exposure, white balance;
- lighting direction/intensity, table/cube textures and backgrounds;
- cube and target pose, size, mass, friction, restitution;
- joint offsets, backlash, damping, motor strength, command latency and noise;
- observation delay, frame drops, action delay and control-period jitter.

Maintain three suites: nominal, measured randomization, and out-of-range stress.
Track performance against each individual perturbation so a single aggregate
score cannot hide a catastrophic weakness.

**Transfer gate:** median full-task success ≥90% nominal and ≥80% under measured
randomization over five seeds and 500 episodes per seed; worst seed ≥70%; zero
hard-limit or forbidden-contact violations in 2,500 transfer-gate episodes.

### WP7 — Package the deployable policy safely

- Export only the actor with a documented preprocessing and joint-order contract.
- Add an inference parity test between the training checkpoint and exported
  artifact on fixed observations.
- Wrap actions with joint-position, velocity, per-step delta, workspace, and
  timeout clamps independent of the learned policy.
- Add camera-staleness detection, communication watchdog, known-safe retreat,
  operator enable/deadman control, and a physical emergency stop.
- Log observation timestamps, raw policy output, clamped command, robot state,
  intervention reason, and synchronized video.

**Gate:** recorded-data replay and no-motion shadow mode produce no interface,
ordering, timing, NaN, stale-frame, or limit errors.

### WP8 — Guarded sim-to-real rollout

Real hardware work begins only after the transfer and safety gates pass:

1. no-motion shadow inference on prerecorded and live images;
2. free-space motion at 10–20% normal speed with no object;
3. supervised reach and retreat without closing the gripper;
4. grasp/hold over a padded workspace;
5. full placement with conservative bounds;
6. randomized real evaluation with every failure retained;
7. optional fine-tuning on a reviewed mixture of simulation and successful real
   trajectories, followed by a fresh held-out real evaluation.

Any watchdog trigger, unexpected contact, repeated drop, calibration mismatch,
or operator stop returns the project to the relevant simulation/calibration
gate. Online exploration directly on the physical arm is out of scope for the
first transfer.

## Video and reporting standard

Each milestone publishes:

- a fixed-seed, non-cherry-picked reel containing every evaluation episode;
- a short side-by-side summary sampled by a rule fixed before looking at videos;
- separate failure reel grouped by failure type;
- native high-resolution render plus the exact 84×84 actor observation;
- plots with per-seed traces and aggregate uncertainty;
- a model card stating observations, action units, limits, task version,
  training data, checkpoint-selection rule, and known failure modes.

Videos must not stop at first contact or lift. Successful pick-place videos show
hold, transport, release, one-second settling, and two seconds after success.

## Execution order

1. Finish WP0 and add regression tests for the current lift task.
2. Implement and validate pick-place-v1 (WP1) with a scripted expert.
3. Build C1–C3 demonstrations and curriculum (WP2–WP3).
4. Run a three-seed development matrix; fix task/data defects, not test scores.
5. Calibrate the real setup without commanding it (WP5).
6. Add measured randomization and C4, then active perception C5 (WP6).
7. Freeze configs and run the five-seed BC/AWR/AAWR comparison (WP4).
8. Pass transfer gates, export the actor, and validate shadow mode (WP7).
9. Start guarded hardware rollout only with explicit operator approval (WP8).

## Definition of ready for real

The project is ready to request a physical-arm trial only when all of the
following are true:

- the full pick-hold-place-settle task and safety tests pass;
- held-out multi-seed transfer metrics meet WP6 gates;
- all evaluation episodes and failure categories are reviewable in HD;
- calibration and policy artifacts are versioned and reproducible;
- actor export passes inference parity and shadow-mode checks;
- independent action clamps, watchdog, retreat, deadman control, and physical
  emergency stop have been tested;
- known limitations and a step-by-step supervised hardware runbook are written.

Isaac Lab is considered only if measured MuJoCo contact/camera limitations block
a gate. It is not a prerequisite by itself and should not replace calibration,
robust evaluation, or hardware safety engineering.
