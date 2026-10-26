#!/usr/bin/env python3
"""Emulate a local mocap sender using the normalized GMR pose convention."""
import argparse
import json
import socket
import time

from general_motion_retargeting.utils.lafan1 import load_bvh_file

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bvh', required=True)
parser.add_argument('--port', type=int, default=9870)
parser.add_argument('--fps', type=float, default=60)
parser.add_argument('--source-fps', type=float, default=90)
parser.add_argument('--seconds', type=float, default=10)
args = parser.parse_args()
if min(args.fps, args.source_fps, args.seconds) <= 0:
    parser.error('Rates and duration must be positive')
frames, _ = load_bvh_file(args.bvh, format='nokov')
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    start = time.perf_counter()
    for i in range(int(args.seconds*args.fps)):
        time.sleep(max(0, start+i/args.fps-time.perf_counter()))
        pose = frames[min(int(i*args.source_fps/args.fps),len(frames)-1)]
        packet = {'joints': {name: [p.tolist(), q.tolist()] for name,(p,q) in pose.items()}}
        sock.sendto(json.dumps(packet).encode(), ('127.0.0.1',args.port))
