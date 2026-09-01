# Stage 2 — Unitree G1 active perception

## First task hypothesis

Use the fixed G1 as a stationary right-arm manipulator. A wrist-mounted camera
starts without a useful view of the target because the target is outside the
field of view or hidden by scene geometry. AAWR must move the arm to reveal and
localize the target, then reach it or hand control to a downstream manipulation
policy.

The pelvis/base is fixed in simulation. Legs, waist, left arm, and all other
inactive joints are held in a nominal pose. The policy controls only these seven
right-arm joints from the current simulation asset:

- shoulder pitch, roll, and yaw;
- elbow;
- wrist roll, pitch, and yaw.

This deliberately reduces G1 to a 7-DoF manipulator for `G1-v0`. It tests the
AAWR integration and active-perception hypothesis without mixing them with
balance and locomotion learning.

## Initial experiment contract

| Component | Initial proposal |
| --- | --- |
| Actor observation | wrist-camera RGB or visual embedding, 7 right-arm joint positions/velocities, action/history state |
| Privileged critic state | target and occluder poses, visibility, contacts, full right-arm state |
| Action | 7 joint-position deltas, end-effector delta pose, or a small set of view-changing primitives |
| Success | target revealed/localized and reached, or valid handoff state achieved |
| Safety metrics | self/scene collisions, joint-limit violations, excessive action or contact force |
| Baselines | scripted camera scan, BC, unprivileged AWR, AAWR |

The first action representation should be selected with a short control smoke
test. End-effector deltas are easier to explore, while joint deltas expose fewer
hidden controller assumptions. Whichever representation is chosen must be
shared by BC, AWR, and AAWR.

## Milestones

1. fix the G1 base and hold every joint except the right arm at its nominal pose;
2. attach and validate the wrist camera and its visibility metric;
3. build a minimal randomized occlusion/search-and-reach scene;
4. define success, safety, privileged state, and the seven-joint action adapter;
5. generate scripted demonstrations and run a one-seed BC smoke test;
6. train AAWR and compare it with matched BC/AWR baselines;
7. evaluate across shared seeds, occlusion levels, and held-out target poses.

## Expansion path

Do not unlock the whole humanoid at once. Increase control authority only after
the previous stage has a reproducible baseline:

1. `G1-v0`: fixed base, right arm only;
2. `G1-v1`: right arm plus waist;
3. `G1-v2`: standing G1 with a fixed balance controller;
4. `G1-v3`: short whole-body viewpoint motions or steps.

The exact hardware embodiment must be recorded before transfer. The current
simulation model exposes seven arm joints, whereas a physical G1 configuration
may have five arm DoF unless the additional wrist axes are installed.

## Definition of done

A headless command trains and evaluates a non-trivial wrist-camera
search-and-reach policy using only the seven right-arm joints. The report must
show task success, target visibility, collisions, and joint-limit failures for
matched BC, AWR, and AAWR runs.
