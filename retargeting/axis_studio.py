#!/usr/bin/env python3
"""Axis Studio local joint transforms -> GMR -> G1 MuJoCo viewer."""
import argparse
import copy
import json
import time
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from trajectory import TrajectoryRecorder


# Same Y-up to Z-up convention used by the pinned GMR BVH loader.
AXIS_TO_GMR = Rotation.from_matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
REQUIRED = {'Hips', 'Spine2', 'LeftArm', 'RightArm', 'LeftForeArm',
            'RightForeArm', 'LeftHand', 'RightHand'}
FULL_BODY_REQUIRED = REQUIRED | {
    'LeftUpLeg', 'RightUpLeg', 'LeftLeg', 'RightLeg',
    'LeftFoot', 'RightFoot',
}


def local_to_gmr(joints, scale=0.01):
    """Compose a complete local skeleton, positions in SDK units, quats wxyz."""
    cache = {}
    visiting = set()

    def world(name):
        if name in cache:
            return cache[name]
        if name in visiting:
            raise ValueError('Skeleton contains a parent cycle')
        visiting.add(name)
        joint = joints[name]
        p = np.asarray(joint['position'], dtype=float)
        q = np.asarray(joint['rotation'], dtype=float)
        if (p.shape != (3,) or q.shape != (4,) or
                not np.isfinite(np.r_[p, q]).all() or
                abs(np.linalg.norm(q) - 1) > 0.01):
            raise ValueError(f'Invalid local transform: {name}')
        rotation = Rotation.from_quat(q[[1, 2, 3, 0]])
        parent = joint['parent']
        if parent is None:
            position = AXIS_TO_GMR.apply(p * scale)
            rotation = AXIS_TO_GMR * rotation
        else:
            parent_p, parent_r = world(parent)
            position = parent_p + parent_r.apply(p * scale)
            rotation = parent_r * rotation
        visiting.remove(name)
        cache[name] = position, rotation
        return cache[name]

    missing = REQUIRED - joints.keys()
    if missing:
        raise ValueError(f'Missing Axis Studio joints: {sorted(missing)}')
    pose = {}
    for name in joints:
        p, rotation = world(name)
        q = rotation.as_quat()
        pose[name] = [p.copy(), q[[3, 0, 1, 2]]]
    for side in ('Left', 'Right'):
        foot = side + 'Foot'
        toe = side + 'ToeBase'
        if foot in pose:
            pose[foot + 'Mod'] = [pose[foot][0].copy(),
                                     pose.get(toe, pose[foot])[1].copy()]
    return pose


class UpperBodyRetargeter:
    """Keep a fixed support pose and solve only the arms and waist."""
    def __init__(self, height):
        import mujoco
        import mink
        from general_motion_retargeting import GeneralMotionRetargeting
        self.ik = GeneralMotionRetargeting(
            src_human='bvh_nokov', tgt_robot='unitree_g1',
            actual_human_height=height)
        self.support = self.ik.configuration.data.qpos.copy()
        self.support[:3] = [0, 0, 0.79]
        self.support[3:7] = [1, 0, 0, 0]
        # Remove leg and root tasks so incoming leg motion cannot drive IK.
        for attr in ('tasks1', 'tasks2'):
            tasks = getattr(self.ik, attr)
            tasks[:] = [task for task in tasks
                        if not hasattr(task, 'frame_name') or
                        any(part in str(task.frame_name) for part in
                            ('shoulder', 'elbow', 'wrist', 'torso'))]
        for attr in ('human_body_to_task1', 'human_body_to_task2'):
            mapping = getattr(self.ik, attr)
            for name in list(mapping):
                if name not in REQUIRED - {'Hips'}:
                    del mapping[name]
        self.fixed = list(range(7))
        fixed_dofs = list(range(6))
        for j in range(self.ik.model.njnt):
            name = mujoco.mj_id2name(self.ik.model, mujoco.mjtObj.mjOBJ_JOINT, j) or ''
            if any(part in name for part in ('hip', 'knee', 'ankle')):
                self.fixed.append(int(self.ik.model.jnt_qposadr[j]))
                fixed_dofs.append(int(self.ik.model.jnt_dofadr[j]))
        projection = np.eye(self.ik.model.nv)[fixed_dofs]

        class FixedSupport(mink.Limit):
            def compute_qp_inequalities(self, configuration, dt):
                return mink.Constraint(G=np.vstack([projection, -projection]),
                                       h=np.zeros(2 * len(projection)))

        self.ik.ik_limits.append(FixedSupport())
        self.ik.configuration.update(self.support)

    def step(self, pose):
        pose = copy.deepcopy(pose)
        # Track gestures relative to a fixed robot pelvis, retaining root rotation.
        offset = self.support[:3] / self.ik.human_scale_table['Hips'] - pose['Hips'][0]
        for p, _ in pose.values():
            p += offset
        self.ik.configuration.data.qpos[self.fixed] = self.support[self.fixed]
        result = self.ik.retarget(pose, align_robot_to_ground=False)
        result[self.fixed] = self.support[self.fixed]
        self.ik.configuration.data.qpos[:] = result
        if not np.isfinite(result).all():
            raise RuntimeError('Nonfinite IK result')
        return result


class FullBodyRetargeter:
    """Retarget the floating base, torso, arms and both legs."""
    def __init__(self, height):
        from general_motion_retargeting import GeneralMotionRetargeting
        self.ik = GeneralMotionRetargeting(
            src_human='bvh_nokov', tgt_robot='unitree_g1',
            actual_human_height=height)
        self.support = self.ik.configuration.data.qpos.copy()

    def step(self, pose):
        missing = FULL_BODY_REQUIRED - pose.keys()
        if missing:
            raise ValueError(f'Missing full-body joints: {sorted(missing)}')
        result = self.ik.retarget(copy.deepcopy(pose), align_robot_to_ground=True)
        if not np.isfinite(result).all():
            raise RuntimeError('Nonfinite IK result')
        return result


class AxisSource:
    def __init__(self, port, rotation_order, avatar_name=None):
        try:
            import mocap_api as sdk
        except ImportError as exc:
            raise RuntimeError('Install the SDK with ./retargeting/setup_axis.sh') from exc
        self.sdk = sdk
        self.avatar_name = avatar_name
        self.selected_avatar = None
        self.app = sdk.MCPApplication()
        settings = sdk.MCPSettings()
        settings.set_udp(port)
        settings.set_bvh_rotation(getattr(sdk.MCPBvhRotation, rotation_order))
        # This SDK release exposes the displacement switch as Transformation.
        settings.set_bvh_transformation(sdk.MCPBvhDisplacement.Enable)
        self.app.set_settings(settings)
        render = sdk.MCPRenderSettings()
        render.set_unit(sdk.MCPUnit.Centimeter)
        self.app.set_render_settings(render)
        ok, reason = self.app.open()
        if not ok:
            raise RuntimeError(f'MocapApi could not open UDP {port}: {reason}')
        print(f'Waiting for Axis Studio on UDP {port}', flush=True)

    def latest(self):
        selected = None
        for event in self.app.poll_next_event():
            if event.event_type != self.sdk.MCPEventType.AvatarUpdated:
                continue
            avatar = self.sdk.MCPAvatar(event.event_data.avatar_handle)
            name = avatar.get_name()
            if self.avatar_name and name != self.avatar_name:
                continue
            if self.selected_avatar is None:
                self.selected_avatar = name
                print(f'Avatar: {name}', flush=True)
            if name == self.selected_avatar:
                selected = avatar
        if selected is None:
            return None
        joints = {}

        def visit(joint, parent):
            name = joint.get_name()
            joints[name] = dict(parent=parent, position=joint.get_local_position(),
                                rotation=joint.get_local_rotation())
            for child in joint.get_children():
                visit(child, name)

        visit(selected.get_root_joint(), None)
        return local_to_gmr(joints)

    def close(self):
        self.app.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=7012)
    parser.add_argument('--rotation-order', choices=['XYZ', 'YXZ', 'ZXY', 'ZYX', 'YZX', 'XZY'], default='YXZ')
    parser.add_argument('--avatar')
    parser.add_argument('--height', type=float, default=1.75)
    parser.add_argument('--fps', type=float, default=60)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--replay-local', type=Path, help='Replay JSONL local transforms without the SDK')
    parser.add_argument('--replay-bvh', type=Path, help='Emulate the SDK local-transform input using a BVH')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--record', type=Path, help='Save timestamped G1 poses to a new .npz file')
    parser.add_argument('--mode', choices=['upper-body', 'full-body'],
                        default='upper-body',
                        help='Fixed-support teleoperation or full-body kinematic IK')
    parser.add_argument('--backend', choices=['gmr', 'pinocchio'], default='gmr',
                        help='IK implementation; Pinocchio requires full-body mode')
    args = parser.parse_args()
    if min(args.height, args.fps, args.seconds) <= 0:
        parser.error('Height, FPS and seconds must be positive')
    if args.replay_local and args.replay_bvh:
        parser.error('Select only one replay source')
    if args.backend == 'pinocchio' and args.mode != 'full-body':
        parser.error('The Pinocchio backend requires --mode full-body')
    source = None
    replay = None
    viewer = None
    recorder = None
    timings = []
    try:
        if args.replay_local:
            replay = iter(args.replay_local.read_text().splitlines())
        elif args.replay_bvh:
            if args.backend == 'pinocchio':
                import sys
                utils_dir = (Path(__file__).resolve().parent / 'GMR' /
                             'general_motion_retargeting' / 'utils')
                sys.path.insert(0, str(utils_dir))
                from lafan_vendor.extract import read_bvh
            else:
                from general_motion_retargeting.utils.lafan_vendor.extract import read_bvh
            anim = read_bvh(str(args.replay_bvh))
            # The included BVH is sampled at 90 Hz.
            def bvh_frames():
                for tick in range(int(args.seconds * args.fps)):
                    frame = min(int(tick * 90 / args.fps), len(anim.pos) - 1)
                    joints = {name: dict(
                        parent=None if anim.parents[i] < 0 else anim.bones[anim.parents[i]],
                        position=anim.pos[frame, i].tolist(),
                        rotation=anim.quats[frame, i].tolist())
                        for i, name in enumerate(anim.bones)}
                    yield json.dumps({'joints': joints})
            replay = iter(bvh_frames())
        else:
            source = AxisSource(args.port, args.rotation_order, args.avatar)
        if args.backend == 'pinocchio':
            from pinocchio_fullbody import PinocchioFullBodyRetargeter
            retargeter = PinocchioFullBodyRetargeter(args.height)
        else:
            retargeter = (UpperBodyRetargeter(args.height)
                          if args.mode == 'upper-body'
                          else FullBodyRetargeter(args.height))
        if args.record:
            if args.backend == 'pinocchio':
                names = list(retargeter.model.names[1:])
            else:
                import mujoco
                model = retargeter.ik.model
                names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j)
                         for j in range(model.njnt)
                         if model.jnt_type[j] != mujoco.mjtJoint.mjJNT_FREE]
            recorder = TrajectoryRecorder(args.record, names, dict(
                robot='unitree_g1',
                mode=('upper_body_fixed_support' if args.mode == 'upper-body'
                      else 'full_body_kinematic'),
                backend=args.backend,
                source='local_transform_replay' if replay is not None else 'axis_studio_sdk',
                nominal_fps=args.fps, height_m=args.height,
                rotation_order=args.rotation_order, clock='local_monotonic_seconds',
                units='meters_radians', root_quaternion_order='wxyz'))
        if not args.headless:
            if args.backend == 'pinocchio':
                from pinocchio_fullbody import PinocchioMotionViewer
                viewer = PinocchioMotionViewer(args.fps)
            else:
                from general_motion_retargeting import RobotMotionViewer
                viewer = RobotMotionViewer('unitree_g1', motion_fps=args.fps)
            support = retargeter.support
            viewer.step(support[:3], support[3:7], support[7:], rate_limit=False)
        start = last_frame = time.perf_counter()
        next_tick = start
        stale = False
        invalid = 0
        while time.perf_counter() - start < args.seconds:
            if viewer and not viewer.viewer.is_running():
                break
            time.sleep(max(0, next_tick - time.perf_counter()))
            next_tick = time.perf_counter() + 1 / args.fps
            try:
                if replay is not None:
                    line = next(replay, None)
                    if line is None:
                        break
                    pose = local_to_gmr(json.loads(line)['joints'])
                else:
                    pose = source.latest()
            except (ValueError, KeyError, TypeError) as exc:
                invalid += 1
                if invalid == 1 or invalid % 60 == 0:
                    print(f'Skipping invalid pose: {exc}', flush=True)
                continue
            if pose is None:
                if time.perf_counter() - last_frame > 1 and not stale:
                    print('No fresh pose for 1 s; holding the last pose.', flush=True)
                    stale = True
                if viewer:
                    viewer.viewer.sync()
                continue
            last_frame = time.perf_counter()
            stale = False
            tick = time.perf_counter()
            qpos = retargeter.step(pose)
            if recorder:
                recorder.append(time.perf_counter() - start, qpos)
            if viewer:
                viewer.step(qpos[:3], qpos[3:7], qpos[7:], rate_limit=False)
            timings.append((time.perf_counter() - tick) * 1000)
        report = dict(frames=len(timings), invalid_frames=invalid,
                      source='local_transform_replay' if replay is not None else 'axis_studio_sdk',
                      p95_ms=float(np.percentile(timings, 95)) if timings else None,
                      mode=args.mode,
                      backend=args.backend,
                      physical_suit_tested=False)
        print(json.dumps(report, indent=2))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + '\n')
    except KeyboardInterrupt:
        print('Axis Studio teleoperation stopped.', flush=True)
    finally:
        try:
            if recorder:
                recorder.close()
        finally:
            try:
                if viewer:
                    viewer.close()
            finally:
                if source:
                    source.close()


if __name__ == '__main__':
    main()
