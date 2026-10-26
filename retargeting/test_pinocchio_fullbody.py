"""Checks for the optional Pinocchio/CasADi full-body backend."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'retargeting'))
sys.path.insert(0, str(ROOT / 'retargeting/GMR/general_motion_retargeting/utils'))

from lafan_vendor.extract import read_bvh
from axis_studio import local_to_gmr
from pinocchio_fullbody import PinocchioFullBodyRetargeter


class PinocchioFullBodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.anim = read_bvh(str(ROOT / 'assets/source/sw2_1_chr01_MAYA.bvh'))

    def pose(self, frame):
        anim = self.anim
        joints = {
            name: dict(
                parent=None if anim.parents[i] < 0 else anim.bones[anim.parents[i]],
                position=anim.pos[frame, i].tolist(),
                rotation=anim.quats[frame, i].tolist(),
            ) for i, name in enumerate(anim.bones)
        }
        return local_to_gmr(joints)

    def test_joint_order_limits_and_leg_motion(self):
        runner = PinocchioFullBodyRetargeter(1.75)
        expected = [
            'left_hip_pitch_joint', 'left_hip_roll_joint',
            'left_hip_yaw_joint', 'left_knee_joint',
            'left_ankle_pitch_joint', 'left_ankle_roll_joint',
            'right_hip_pitch_joint', 'right_hip_roll_joint',
            'right_hip_yaw_joint', 'right_knee_joint',
            'right_ankle_pitch_joint', 'right_ankle_roll_joint',
        ]
        self.assertEqual(list(runner.model.names[1:13]), expected)
        outputs = np.asarray([runner.step(self.pose(frame))
                              for frame in range(2, 182, 15)])
        self.assertEqual(outputs.shape, (12, 36))
        self.assertTrue(np.isfinite(outputs).all())
        joints = outputs[:, 7:]
        self.assertTrue((joints >= runner.model.lowerPositionLimit - 1e-9).all())
        self.assertTrue((joints <= runner.model.upperPositionLimit + 1e-9).all())
        self.assertGreater(float(np.max(np.ptp(joints[:, :12], axis=0))), 0.01)


if __name__ == '__main__':
    unittest.main()
