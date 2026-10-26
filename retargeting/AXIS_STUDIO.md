# Axis Studio teleoperation in MuJoCo

Axis Studio sends the current Noitom suit pose to the Linux computer over UDP.
Noitom MocapApi decodes the skeleton, GMR solves the arm and waist pose, and
MuJoCo displays G1. The robot base and legs stay fixed. The 29-DoF model does
not reproduce finger motion.

The SDK connection follows the approach in
[RomanSentsov/unitree-g1-axis-studio-retarget](https://github.com/RomanSentsov/unitree-g1-axis-studio-retarget)
at commit `be0a8e0`. This implementation uses GMR and a MuJoCo viewer.

## Installation

From the repository root on Linux:

```bash
./retargeting/setup.sh
./retargeting/setup_axis.sh
```

The second command installs MocapApi 0.1.5 from the pinned reference repository.
It checks out only its SDK directory into ignored `.deps/`. To use an existing
SDK distribution, pass the folder containing its `setup.py`:

```bash
./retargeting/setup_axis.sh /path/to/MocapApi
```

## Axis Studio settings

1. Put the Windows Axis Studio computer and the Linux MuJoCo computer on the
   same network. Find the Linux address with `hostname -I`.
2. In Axis Studio broadcasting settings, enable BVH UDP output. Set the target
   IP to the Linux computer and the target port to `7012`.
3. Set the BVH rotation order to `YXZ` and enable displacement data. The SDK
   requests positions in centimeters; the adapter converts them to meters.
4. Select **BVH - Capturing** for the live suit, or **BVH - Edit** to send a
   recording from Axis Studio. Calibrate the suit and start the broadcast.
5. Allow incoming UDP `7012` on the Linux computer if its firewall blocks it.

Axis Studio menu labels can differ by version. The reference project's
[settings screenshot](https://github.com/RomanSentsov/unitree-g1-axis-studio-retarget/blob/be0a8e0d713697acce94e8b97c49009bc47a3452/docs/image.png)
shows the broadcasting panel.

## Launch

```bash
.venv-gmr/bin/python retargeting/axis_studio.py \
  --port 7012 --rotation-order YXZ \
  --height 1.75 --fps 60 --seconds 3600
```

Set `--height` to the performer's height in meters. If Axis Studio uses another
rotation order, pass the same order to `--rotation-order`. For multiple avatars,
select one with `--avatar NAME`; otherwise the first received avatar is selected.

The program prints the avatar name when it receives a pose. It polls the SDK at
the requested maximum rate and uses the newest available avatar update. If the
stream stops for one second, it prints a message and holds the last pose.
Close the viewer or press Ctrl+C to stop.

No ROS 2, Unitree SDK or trained policy is needed for this simulation.

## Test without a suit

This command emulates the SDK local-transform input from the included 90 FPS
BVH and shows upper-body teleoperation:

```bash
.venv-gmr/bin/python retargeting/axis_studio.py \
  --replay-bvh assets/source/sw2_1_chr01_MAYA.bvh \
  --fps 60 --seconds 20
```

Add `--headless` to run without a window. To run conversion and support-pose
checks:

```bash
.venv-gmr/bin/python retargeting/test_axis_studio.py
```

The checks compare local-to-global conversion with the GMR BVH loader, reject
invalid skeletons, and verify finite arm motion with fixed legs and base.
Local-transform replay does not exercise Axis Studio's binary network protocol.
SDK import and UDP initialization can be checked without a sender:

```bash
.venv-gmr/bin/python retargeting/axis_studio.py --headless --seconds 5
```

A live suit connection still needs validation on an Axis Studio machine.
