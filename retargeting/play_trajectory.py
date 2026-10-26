#!/usr/bin/env python3
"""Replay recorded G1 poses using their actual capture timestamps."""
import argparse
import time
from pathlib import Path

import numpy as np

from trajectory import recover_trajectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trajectory', type=Path)
    parser.add_argument('--speed', type=float, default=1)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--recover-to', type=Path, help='Recover a .npz.partial journal into NPZ')
    args = parser.parse_args()
    if args.recover_to:
        recover_trajectory(args.trajectory, args.recover_to)
        print(f'Recovered: {args.recover_to}')
        return
    if args.speed <= 0:
        parser.error('--speed must be positive')
    with np.load(args.trajectory, allow_pickle=False) as data:
        timestamps = data['timestamps_s'].copy()
        qpos = data['qpos'].copy()
    if (not len(timestamps) or qpos.shape != (len(timestamps), 36) or
            not np.isfinite(qpos).all() or not np.isfinite(timestamps).all() or
            np.any(np.diff(timestamps) <= 0)):
        raise ValueError('Invalid trajectory')
    viewer = None
    try:
        if not args.headless:
            from general_motion_retargeting import RobotMotionViewer
            viewer = RobotMotionViewer('unitree_g1')
        start = time.perf_counter()
        for timestamp, pose in zip(timestamps, qpos):
            if viewer:
                if not viewer.viewer.is_running():
                    break
                time.sleep(max(0, start+(timestamp-timestamps[0])/args.speed-time.perf_counter()))
                viewer.step(pose[:3], pose[3:7], pose[7:], rate_limit=False)
        print(f'Trajectory: {len(qpos)} frames, {timestamps[-1]-timestamps[0]:.3f} s')
    except KeyboardInterrupt:
        pass
    finally:
        if viewer:
            viewer.close()


if __name__ == '__main__':
    main()
