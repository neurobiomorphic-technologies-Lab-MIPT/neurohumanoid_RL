# Stage 1 pilot report

## Status

The SO-101 MuJoCo environment, expert-data conversion, AAWR adapter, and an
end-to-end CUDA training path are working. A 10k-update AAWR run completed;
the matched BC/AWR/AAWR experiment is not yet started.

## Verified data

- public source: 50 SimStudio leader-teleoperation episodes;
- recovered and physics-validated reset profiles: 41;
- generated lift episodes: 164/164 successful;
- transitions: 9,020;
- success threshold: cube centre at or above 8 cm.

The curriculum begins near the grasp, 25 frames before gripper closure. This is
an integration curriculum, not a claim that the policy can reach from home.

![Validated SO-101 expert lift](assets/expert_lift.gif)

The GIF shows replayed expert data. It does not show a learned policy.

## AAWR seed-41 run

Configuration: 5,000 requested offline updates, 10,000 total updates, ten
evaluation episodes, one front RGB camera for the actor, 34-D privileged state
for the critic, and six joint-delta actions.

| Update | Success | Mean episode length |
| ---: | ---: | ---: |
| 140 | 0/10 | 140.0 |
| 1,120 | 1/10 | 131.2 |
| 3,080 | 3/10 | 117.6 |
| 4,060 | 5/10 | 100.1 |
| 5,040 | 5/10 | 87.1 |
| 8,109 | 5/10 | 82.8 |
| 9,066 | 0/10 | 140.0 |
| 10,000 | 3/10 | 104.0 |

The run finished successfully in 5 minutes 14 seconds. It learned a partial
policy, reaching 50% evaluation success at three checkpoints, but regressed and
ended at 30%. This is evidence that the integration learns something, not a
stable solved task. The next useful step is checkpoint saving/selection and a
matched BC/AWR/AAWR seed matrix before expanding the curriculum toward home.

## Seed-41 baseline comparison

All three methods were run for 10,000 updates with the same demonstrations and
evaluation protocol.

| Method | Best success | Final success |
| --- | ---: | ---: |
| BC | 8/10 | 8/10 |
| AWR | 6/10 | 2/10 |
| AAWR | 5/10 | 3/10 |

[Watch the non-cherry-picked evaluation reel](assets/all_eval_checkpoints.mp4).
It includes fixed checkpoints and failure rollouts for all three methods. Only
the first episode of each ten-episode evaluation batch was recorded by the
upstream logger, so the overlaid batch rate—not one clip—is the metric.

On this single seed and near-grasp curriculum, BC is the strongest baseline.
This is not yet a statistically meaningful algorithm ranking; multiple seeds
and best-checkpoint evaluation are required.

## Costs and discarded checks

- external/API cost: zero; WandB is disabled;
- final 10k run: 5 minutes 14 seconds on the local RTX 3080 Ti Laptop GPU;
- earlier valid 2k pilot: 63 seconds;
- one unseeded 2k diagnostic pilot: 63 seconds, retained locally but invalid;
- one video-compatibility attempt stopped after about four training seconds;
- simulator checkout: approximately 31 MB;
- reference parquet: approximately 2.5 MB; large source videos were not downloaded.

The first two pilots are excluded from reported results: one exposed a missing
`success` alias and the other exposed an unseeded Gymnasium reset stream.
