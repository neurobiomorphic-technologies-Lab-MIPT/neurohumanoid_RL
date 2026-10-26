#!/usr/bin/env python3
"""Retarget timestamped poses, using paced BVH playback or UDP JSON input."""
import argparse
import copy
import json
import platform
import socket
import time
from pathlib import Path

import numpy as np
from general_motion_retargeting import GeneralMotionRetargeting
from general_motion_retargeting.utils.lafan1 import load_bvh_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bvh', type=Path)
    parser.add_argument('--udp-port', type=int)
    parser.add_argument('--fps', type=float, default=60)
    parser.add_argument('--source-fps', type=float, default=90)
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--height', type=float, default=1.75)
    parser.add_argument('--viewer', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if bool(args.bvh) == bool(args.udp_port):
        parser.error('Specify exactly one of --bvh or --udp-port')
    if min(args.fps, args.source_fps, args.seconds) <= 0:
        parser.error('Rates and duration must be positive')
    frames = None
    if args.bvh:
        frames, args.height = load_bvh_file(str(args.bvh), format='nokov')
    retargeter = GeneralMotionRetargeting(
        src_human='bvh_nokov', tgt_robot='unitree_g1', actual_human_height=args.height)
    viewer = None
    if args.viewer:
        from general_motion_retargeting import RobotMotionViewer
        viewer = RobotMotionViewer('unitree_g1', motion_fps=args.fps)
    sock = None
    if args.udp_port:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', args.udp_port))
        sock.settimeout(1)
    solve_ms, total_ms, late_ms = [], [], []
    invalid_packets = 0
    start = time.perf_counter()
    index = 0
    try:
        while time.perf_counter() - start < args.seconds:
            if frames is not None:
                deadline = start + index / args.fps
                time.sleep(max(0, deadline - time.perf_counter()))
                source_index = min(int((time.perf_counter()-start)*args.source_fps), len(frames)-1)
                pose = copy.deepcopy(frames[source_index])
            else:
                try:
                    packet, _ = sock.recvfrom(65535)
                    # Drain pending packets so stale poses cannot build a queue.
                    sock.setblocking(False)
                    while True:
                        try:
                            packet, _ = sock.recvfrom(65535)
                        except BlockingIOError:
                            break
                    sock.settimeout(1)
                    payload = json.loads(packet)
                    pose = {name: [np.asarray(p, dtype=float), np.asarray(q, dtype=float)]
                            for name, (p, q) in payload['joints'].items()}
                    for p, q in pose.values():
                        if p.shape != (3,) or q.shape != (4,) or not np.isfinite(np.r_[p,q]).all() or abs(np.linalg.norm(q)-1)>0.01:
                            raise ValueError('Invalid pose')
                    deadline = time.perf_counter()
                except socket.timeout:
                    continue
                except (ValueError, KeyError, TypeError):
                    invalid_packets += 1
                    continue
            tick = time.perf_counter()
            qpos = retargeter.retarget(pose, align_robot_to_ground=True, ground_clearance=0.002)
            solved = time.perf_counter()
            if not np.isfinite(qpos).all():
                raise RuntimeError('Nonfinite retargeting output')
            if viewer:
                viewer.step(qpos[:3], qpos[3:7], qpos[7:], rate_limit=False, follow_camera=True)
            end = time.perf_counter()
            solve_ms.append((solved-tick)*1000)
            total_ms.append((end-tick)*1000)
            late_ms.append(max(0, end-deadline-1/args.fps)*1000)
            index += 1
    finally:
        if sock:
            sock.close()
        if viewer:
            viewer.close()
    report = dict(cpu=platform.processor(), target_fps=args.fps, frames=index,
                  elapsed_s=time.perf_counter()-start, viewer=args.viewer,
                  source='paced_bvh' if frames is not None else 'udp', invalid_packets=invalid_packets)
    if index:
        report.update(solve_p50_ms=float(np.median(solve_ms)), solve_p95_ms=float(np.percentile(solve_ms,95)),
                      solve_max_ms=float(max(solve_ms)), total_p95_ms=float(np.percentile(total_ms,95)),
                      missed_deadline_percent=100*sum(x>0 for x in late_ms)/index)
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
