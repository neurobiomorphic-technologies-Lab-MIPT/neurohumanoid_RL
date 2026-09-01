# Stage 1 — LeRobot arm active perception

## First task hypothesis

Place a target behind an occluder so that a direct reach from the initial camera
view is unreliable. The policy must first obtain task-relevant information and
then reach or hand off to a grasp controller.

## Initial experiment contract

| Component | Initial proposal |
| --- | --- |
| Actor observation | RGB or compact visual embedding, joint state, action/history state |
| Privileged critic state | target and occluder poses, contacts, visibility, task phase |
| Action | camera/arm delta pose or a small set of view-changing primitives |
| Success | target revealed and reached/grasped within the horizon |
| Baselines | BC, AWR, AAWR |

## Decisions to pin before implementation

- exact LeRobot arm model;
- simulator and robot asset revision;
- wrist-mounted versus external movable camera;
- end-to-end reach/grasp versus handoff to an existing grasp policy;
- demonstration generator and reset randomization ranges.

## Milestones

1. deterministic scene and scripted oracle rollout;
2. visibility metric and privileged-state adapter;
3. demonstration dataset and BC smoke test;
4. AAWR training run;
5. matched multi-seed comparison and occlusion-level evaluation.

## Definition of done

AAWR is evaluated against matched BC/AWR baselines on held-out scene
randomizations, with success and target-visibility curves plus rollout videos.
