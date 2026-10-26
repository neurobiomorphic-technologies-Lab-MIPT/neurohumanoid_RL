"""Full-body G1 IK with Pinocchio, CasADi and IPOPT.

The optimization layout follows Roman Sentsov's arm retargeter, but uses the
project's licensed 29-DoF rubber-hand URDF and adds torso and leg targets.
"""
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


TARGETS = (
    ('torso_link', 'Spine2', 20.0, 2.0, 0.90),
    ('left_elbow_link', 'LeftForeArm', 8.0, 0.0, 0.75),
    ('right_elbow_link', 'RightForeArm', 8.0, 0.0, 0.75),
    ('left_rubber_hand', 'LeftHand', 35.0, 1.0, 0.75),
    ('right_rubber_hand', 'RightHand', 35.0, 1.0, 0.75),
    ('left_knee_link', 'LeftLeg', 10.0, 0.0, 0.90),
    ('right_knee_link', 'RightLeg', 10.0, 0.0, 0.90),
    ('left_ankle_roll_link', 'LeftFootMod', 45.0, 2.0, 0.90),
    ('right_ankle_roll_link', 'RightFootMod', 45.0, 2.0, 0.90),
)


class PinocchioFullBodyRetargeter:
    """Warm-started full-body nonlinear IK for the G1 29-DoF model."""

    def __init__(self, height):
        try:
            import casadi
            import pinocchio as pin
            from pinocchio import casadi as cpin
        except ImportError as exc:
            raise RuntimeError(
                'Pinocchio backend is missing. Run ./retargeting/setup_pinocchio.sh'
            ) from exc

        self.casadi = casadi
        self.pin = pin
        self.height_ratio = 1.8 / height
        root = Path(__file__).resolve().parents[1]
        urdf = root / 'retargeting/GMR/assets/unitree_g1/g1_custom_collision_29dof.urdf'
        self.model = pin.buildModelFromUrdf(str(urdf))
        if self.model.nq != 29:
            raise RuntimeError(f'Expected 29 G1 joints, URDF has {self.model.nq}')
        self.data = self.model.createData()
        self.q = pin.neutral(self.model)
        self.support = np.r_[np.array([0., 0., 0.79, 1., 0., 0., 0.]), self.q]
        self.calibration = None
        self.initial_hips_pos = None
        self.initial_hips_rot = None
        pin.framesForwardKinematics(self.model, self.data, self.q)
        self.neutral_frames = {
            frame_name: (
                self.data.oMf[self.model.getFrameId(frame_name)].translation.copy(),
                self.data.oMf[self.model.getFrameId(frame_name)].rotation.copy(),
            ) for frame_name, *_ in TARGETS
        }

        cmodel = cpin.Model(self.model)
        cdata = cmodel.createData()
        cq = casadi.SX.sym('q', self.model.nq, 1)
        cpin.framesForwardKinematics(cmodel, cdata, cq)
        self.opti = casadi.Opti()
        self.var_q = self.opti.variable(self.model.nq)
        self.last_q = self.opti.parameter(self.model.nq)
        self.parameters = []
        cost = 0
        for frame_name, _, pos_weight, rot_weight, _ in TARGETS:
            frame_id = self.model.getFrameId(frame_name)
            if frame_id >= self.model.nframes:
                raise RuntimeError(f'URDF frame not found: {frame_name}')
            target = self.opti.parameter(4, 4)
            self.parameters.append(target)
            frame = cdata.oMf[frame_id]
            position = casadi.Function(
                f'{frame_name}_position', [cq], [frame.translation])
            orientation = casadi.Function(
                f'{frame_name}_orientation', [cq], [frame.rotation])
            cost += pos_weight * casadi.sumsqr(
                position(self.var_q) - target[:3, 3])
            if rot_weight:
                cost += rot_weight * casadi.sumsqr(
                    orientation(self.var_q) - target[:3, :3])
        cost += 0.08 * casadi.sumsqr(self.var_q)
        cost += 0.30 * casadi.sumsqr(self.var_q - self.last_q)
        self.opti.minimize(cost)
        self.opti.subject_to(self.opti.bounded(
            self.model.lowerPositionLimit, self.var_q,
            self.model.upperPositionLimit))
        self.opti.solver('ipopt', {
            'expand': True,
            'print_time': False,
            'ipopt.sb': 'yes',
            'ipopt.print_level': 0,
            'ipopt.max_iter': 35,
            'ipopt.tol': 1e-4,
            'ipopt.acceptable_tol': 5e-4,
            'ipopt.warm_start_init_point': 'yes',
        })

    @staticmethod
    def _rotation(wxyz):
        q = np.asarray(wxyz, dtype=float)
        return Rotation.from_quat(q[[1, 2, 3, 0]])

    def step(self, pose):
        required = {'Hips'} | {human for _, human, *_ in TARGETS}
        missing = required - pose.keys()
        if missing:
            raise ValueError(f'Missing Pinocchio targets: {sorted(missing)}')
        hips_pos = np.asarray(pose['Hips'][0], dtype=float)
        hips_rot = self._rotation(pose['Hips'][1])
        inv_hips = hips_rot.inv()
        relative = []
        for frame_name, human, _, _, scale in TARGETS:
            position = inv_hips.apply(
                np.asarray(pose[human][0]) - hips_pos) * scale * self.height_ratio
            orientation = (inv_hips * self._rotation(pose[human][1])).as_matrix()
            relative.append((position, orientation))
        if self.calibration is None:
            self.initial_hips_pos = hips_pos.copy()
            self.initial_hips_rot = hips_rot
            self.calibration = []
            for (frame_name, *_), (position, orientation) in zip(TARGETS, relative):
                neutral_pos, neutral_rot = self.neutral_frames[frame_name]
                self.calibration.append((neutral_pos - position,
                                         orientation.T @ neutral_rot))
        for parameter, (position, orientation), (pos_offset, rot_offset) in zip(
                self.parameters, relative, self.calibration):
            target = np.eye(4)
            target[:3, 3] = position + pos_offset
            target[:3, :3] = orientation @ rot_offset
            self.opti.set_value(parameter, target)
        self.opti.set_value(self.last_q, self.q)
        self.opti.set_initial(self.var_q, self.q)
        try:
            solution = self.opti.solve()
            solved = np.asarray(solution.value(self.var_q)).reshape(-1)
        except RuntimeError:
            solved = np.asarray(self.opti.debug.value(self.var_q)).reshape(-1)
        solved = np.clip(solved, self.model.lowerPositionLimit,
                         self.model.upperPositionLimit)
        # Same four-sample weighted filter as the reference implementation.
        if not hasattr(self, '_history'):
            self._history = []
        self._history.insert(0, solved)
        self._history = self._history[:4]
        weights = np.array([0.4, 0.3, 0.2, 0.1])[:len(self._history)]
        self.q = np.average(self._history, axis=0, weights=weights)

        root = self.support[:3] + self.initial_hips_rot.inv().apply(
            hips_pos - self.initial_hips_pos) * (0.90 * self.height_ratio)
        root_q_xyzw = (self.initial_hips_rot.inv() * hips_rot).as_quat()
        root_q_wxyz = root_q_xyzw[[3, 0, 1, 2]]
        result = np.r_[root, root_q_wxyz, self.q]
        if result.shape != (36,) or not np.isfinite(result).all():
            raise RuntimeError('Invalid Pinocchio IK result')
        return result


class PinocchioMotionViewer:
    """Small MuJoCo viewer that does not import the Torch-dependent GMR API."""
    def __init__(self, motion_fps):
        import mujoco
        import mujoco.viewer
        root = Path(__file__).resolve().parents[1]
        xml = root / 'retargeting/GMR/assets/unitree_g1/g1_mocap_29dof.xml'
        self.mujoco = mujoco
        self.model = mujoco.MjModel.from_xml_path(str(xml))
        self.data = mujoco.MjData(self.model)
        self.viewer = mujoco.viewer.launch_passive(self.model, self.data)

    def step(self, root_pos, root_rot, joint_pos, rate_limit=False):
        self.data.qpos[:] = np.r_[root_pos, root_rot, joint_pos]
        self.mujoco.mj_forward(self.model, self.data)
        self.viewer.sync()

    def close(self):
        self.viewer.close()
