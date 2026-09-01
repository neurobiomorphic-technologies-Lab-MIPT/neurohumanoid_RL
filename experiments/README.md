# Experiments

Each subdirectory is an experiment card and, later, the home for its runnable
configuration and result report.

The common progression is:

1. make the environment reset and step deterministically;
2. generate or import demonstrations;
3. run a one-seed BC smoke test;
4. compare BC, AWR, and AAWR with matched budgets;
5. run multiple seeds and privileged-state ablations;
6. record metrics, videos, failures, and the next decision.

Every runnable experiment should expose these fields in a resolved config:

- actor observations;
- privileged critic observations;
- action space and control frequency;
- reward and termination conditions;
- dataset identity and demonstration count;
- training/evaluation budget and seeds;
- output directory and code revision.
