# Stage 0 result report

## Protocol

- AAWR revision: `05845db6c0da25993e816c44f47c123487f20cd1`
- gym-xarm revision: `388227ab683516d014bb7273350ac78c10faf84b`
- dataset: `stage0_xarm_seed41`, 100 scripted demonstrations
- methods: BC, unprivileged AWR, AAWR
- shared seeds: 41, 42, 43
- offline updates: 20,000
- total updates: 40,000
- external logging: disabled

## Smoke tests

Environment reset/step/render and 50-update BC, AWR, and AAWR GPU smoke tests
completed successfully on 2026-09-02. A zero success rate after only 50 updates
is expected and is not treated as an experiment result.

## Main comparison

All nine matched runs are complete.

| Method | Seed 41 | Seed 42 | Seed 43 | Mean ± sample SD |
| --- | ---: | ---: | ---: | ---: |
| BC | 0.000 | 0.000 | 0.000 | 0.000 ± 0.000 |
| AWR | 0.225 | 0.025 | 0.125 | 0.125 ± 0.100 |
| AAWR | 0.975 | 1.000 | 0.975 | 0.983 ± 0.014 |

These are final success rates over 40 evaluation episodes at 40,000 updates.
AAWR also finishes much faster: final mean episode lengths are 17.575, 16.775,
and 17.575 steps, compared with 44.925, 49.450, and 46.350 for AWR.

![BC, AWR, and AAWR xArm rollouts](assets/bc_awr_aawr_seed41.gif)

## Compute and storage cost

- Successful 3×3 matrix wall-clock: 3 h 46 min 35 s, sequential on one local
  RTX 3080 Ti Laptop GPU.
- Peak observed training allocation: approximately 1.6 GiB VRAM for AAWR and
  under 1 GiB for BC.
- External/API cost: zero; WandB and all remote experiment logging were disabled.
- Generated dataset storage: approximately 381 MiB including the retained
  compatibility dataset; tracked GIF: 1.1 MiB.
- Two failed BC attempts reached the 20,000-step boundary before the upstream
  signature bug was identified; they add roughly 19 minutes outside the
  successful-matrix figure above.

## Privileged-state ablations

Not started. Run only after the matched main comparison is complete.

## Deviations and limitations

- The AAWR `environment.yaml` and gym-xarm Poetry lock are not mutually
  compatible with the repositories' current xArm code. The deployed versions
  are pinned explicitly in this repository.
- The upstream evaluation CSV originally records reward only. The local logging
  patch additionally records success and episode length without changing
  training behavior.
- Upstream BC stops at the offline-to-online boundary because `train_il.py`
  passes a `demo_buffer` keyword that `BC.update()` does not accept. The local
  compatibility patch accepts and ignores this unused argument.
