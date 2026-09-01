# Stage 2 — Unitree G1 active perception

## First task hypothesis

Teach G1 to reveal and localize a target that is initially outside the camera's
field of view or hidden by scene geometry, then finish in a stable pose from
which a downstream task can proceed.

The first version should train active perception above an existing low-level
controller. Candidate AAWR actions are head/torso gaze targets, short viewpoint
changes, or discrete motion primitives. Whole-body torque learning is out of
scope for the first AAWR run.

## Initial experiment contract

| Component | Initial proposal |
| --- | --- |
| Actor observation | deployable camera input, proprioception, observation/action history |
| Privileged critic state | target pose, geometry/occlusion state, contacts, base state |
| Action | high-level viewpoint or motion command |
| Success | target visible/localized and G1 stable in a task-relevant pose |
| Safety metrics | falls, collisions, joint-limit violations, unstable terminations |
| Baselines | scripted scan, BC, AWR, AAWR |

## Milestones

1. import G1 and a minimal occlusion/search scene;
2. connect a stable low-level controller and verify randomized resets;
3. define target visibility, success, safety, and privileged state;
4. generate coarse or scripted demonstrations;
5. train one-seed BC and AAWR smoke tests;
6. compare methods across shared seeds and held-out target placements.

## Definition of done

A headless command trains and evaluates a non-trivial search/viewpoint policy,
and the report shows task success together with stability and safety failures.
