# Stage 0 — official AAWR simulation reproduction

## Question

Can the public AAWR implementation reproduce its documented advantage over BC
and unprivileged AWR on the toy simulated xArm lift task?

## Upstream starting point

- Code: <https://github.com/penn-pal-lab/aawr>
- Environment: `gym-xarm`, linked by the upstream setup instructions
- Training entrypoint: `src/train_il.py`
- Initial task: `gymnasium_xarm_lift`

Pin both upstream revisions here before changing code:

```text
aawr commit: TODO
gym-xarm commit: TODO
```

## Run matrix

| Method | Actor input | Critic input | Required |
| --- | --- | --- | --- |
| BC | partial observation | — | Yes |
| AWR | partial observation | partial observation | Yes |
| AAWR | partial observation | privileged state + actor state | Yes |

Use a one-seed smoke test first, then at least three shared seeds for the main
comparison. Follow with full/noisy/zero privileged-state ablations.

## Outputs

- environment and installation notes;
- pinned source revisions and dataset manifest;
- exact commands and resolved configs;
- per-seed success rate, return, and episode length;
- aggregate learning curves and rollout videos;
- a short report explaining differences from upstream results.

## Definition of done

A clean checkout can execute a headless smoke test and reproduce a documented,
matched-budget BC/AWR/AAWR comparison.
