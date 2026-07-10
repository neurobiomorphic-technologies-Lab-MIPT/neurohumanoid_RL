# neurohumanoid_RL

Robot deploy package for the Unitree G1 dance controller.

This branch is intended to keep only the robot-side deploy code/assets needed
to rebuild and run the controller on the robot. Training/simulation experiments
are intentionally not included here.

## Contents

- `deploy/include/` — shared controller/FSM/IsaacLab-style deploy headers.
- `deploy/robots/g1/` — G1 controller source, config, and policies.
- `deploy/robots/g1/config/policy/mimic/`:
  - `dance1_subject2` — full dance, about 131s.
  - `dance1_subject2_1mx1_10s` — compact 10s clip.
  - `dance1_subject2_16s_faststart` — fast-start clip, 16.24s.
- `deploy/thirdparty/` — vendored CNPY and ONNXRuntime for x64/aarch64.
- `RUN_WORKING_10S.txt` — last known robot run notes.

Build directories are ignored and should be regenerated on the robot.

## If robot environment is already installed

If this repo is already copied/cloned on the robot and `g1_ctrl` has already
been built, just run:

```bash
cd /home/unitree/unitree_dance/deploy/robots/g1/build
LD_LIBRARY_PATH=/usr/local/lib:/usr/local/cuda-11.4/lib64 ./g1_ctrl --network=eth0
```

Then on the controller:

1. `L2+Up` — enter FixStand.
2. `R2+A` — enter Velocity.
3. `R1+A` — start full dance, or `R1+B` for 10s, or `R1+Y` for 16.24s.

## Build on robot

```bash
cd /home/unitree/unitree_dance/deploy/robots/g1
rm -rf build
mkdir build
cd build
cmake ..
make -j"$(nproc)"
```

## Run on robot

```bash
cd /home/unitree/unitree_dance/deploy/robots/g1/build
LD_LIBRARY_PATH=/usr/local/lib:/usr/local/cuda-11.4/lib64 ./g1_ctrl --network=eth0
```

Controller mappings from the current deploy:

- `L2+Up` — FixStand.
- `R2+A` — Velocity / exit dance to Velocity.
- `R1+A` — full dance.
- `R1+B` — compact 10s dance clip.
- `R1+Y` — 16.24s fast-start clip.
- `L2+B` — Passive.
