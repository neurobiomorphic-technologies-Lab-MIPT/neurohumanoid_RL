# Real-time G1 retargeting in MuJoCo

The runner accepts one global human pose at a time, solves GMR inverse
kinematics and updates the G1 viewer. This is geometric playback. Joint targets
are not passed through a balance policy or a physical robot controller.

Install GMR with `./retargeting/setup.sh`, then run from the repository root:

```bash
.venv-gmr/bin/python retargeting/realtime.py \
  --bvh assets/source/sw2_1_chr01_MAYA.bvh \
  --fps 60 --seconds 30 --viewer
```

The BVH is preloaded before timing starts. Frames are released at the requested
rate; when processing falls behind, playback selects the current source frame.
Reports measure IK, viewer submission and local deadline misses. They do not
measure sensor latency, display scanout or network transit.

## UDP input

Start the receiver, then run the sender in another terminal:

```bash
.venv-gmr/bin/python retargeting/realtime.py \
  --udp-port 9870 --fps 60 --seconds 60 --viewer
```

```bash
.venv-gmr/bin/python retargeting/replay_udp.py \
  --bvh assets/source/sw2_1_chr01_MAYA.bvh \
  --port 9870 --fps 60 --seconds 30
```

The receiver binds to localhost and drains queued packets before solving the
latest pose. The JSON message has this structure:

```json
{"joints": {"Hips": [[0.0, 0.0, 0.9], [1.0, 0.0, 0.0, 0.0]]}}
```

Each entry contains a world position in meters and a normalized quaternion in
`wxyz` order. Send the complete skeleton with names matching the GMR Nokov
profile, including `LeftFootMod` and `RightFootMod`. The example above shows
only the field layout. `replay_udp.py` produces complete messages with the
required coordinate conversion. Connecting a physical suit requires an adapter
from its SDK into this format; no physical suit was used for these tests.

## Measured performance

Test machine: Intel Core i9-12900H, Linux. GMR IK runs on CPU. The laptop has
an NVIDIA RTX 3080 Ti Laptop GPU for graphics. Each paced BVH trial lasted
10 seconds using the included sword motion. Initialization and BVH loading are
excluded. Reports are stored in `benchmarks/`.

| Target | Viewer | IK median | IK p95 | Processing p95 | Deadline misses |
| --- | --- | --- | --- | --- | --- |
| 30 Hz | Off | 4.47 ms | 6.62 ms | 6.62 ms | 0% |
| 60 Hz | Off | 4.18 ms | 5.82 ms | 5.83 ms | 0% |
| 90 Hz | Off | 4.36 ms | 6.65 ms | 6.66 ms | 4.66% |
| 60 Hz | On | 5.06 ms | 6.83 ms | 10.49 ms | 0% |

Use 60 Hz on this machine. The 90 Hz trial shows occasional scheduling or
processing overruns. Longer sessions and a live suit still need measurement.

The separate localhost UDP test processed all 600 poses sent over 10 seconds
at 60 Hz, with no malformed packets. IK p95 was 6.61 ms. The receiver stayed
open for 25 seconds to include sender startup and idle time, so its total
runtime must not be interpreted as stream throughput.

To save a new timing report, add `--report benchmarks/my_run.json`.
