#!/usr/bin/env python3
"""Render a recorded G1 trajectory to MP4 with a pelvis-following camera."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('MUJOCO_GL', 'egl')

import imageio.v2 as imageio
import mujoco
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trajectory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fps', type=float)
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    args = parser.parse_args()
    if min(args.width, args.height) <= 0:
        parser.error('Width and height must be positive')

    archive = np.load(args.trajectory, allow_pickle=False)
    qpos = np.asarray(archive['qpos'], dtype=float)
    metadata = json.loads(str(archive['metadata_json']))
    fps = args.fps or float(metadata.get('nominal_fps', 30))
    if qpos.ndim != 2 or qpos.shape[1] != 36 or not np.isfinite(qpos).all():
        raise ValueError('Expected finite qpos with shape (N, 36)')

    root = Path(__file__).resolve().parents[1]
    xml = root / 'retargeting/GMR/assets/unitree_g1/g1_mocap_29dof.xml'
    model = mujoco.MjModel.from_xml_path(str(xml))
    model.vis.global_.offwidth = args.width
    model.vis.global_.offheight = args.height
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=args.height, width=args.width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.distance = 3.0
    camera.azimuth = 135
    camera.elevation = -12
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with imageio.get_writer(args.output, fps=fps, codec='libx264',
                            quality=8, macro_block_size=None) as writer:
        for pose in qpos:
            data.qpos[:] = pose
            mujoco.mj_forward(model, data)
            camera.lookat[:] = data.xpos[1]
            camera.lookat[2] += 0.15
            renderer.update_scene(data, camera=camera)
            writer.append_data(renderer.render())
    renderer.close()
    print(f'Video saved: {args.output} ({len(qpos)} frames at {fps:g} FPS)')


if __name__ == '__main__':
    main()
