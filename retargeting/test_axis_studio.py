"""Check Axis local-transform conversion against the pinned GMR BVH loader."""
import copy
import unittest
from pathlib import Path

import numpy as np

from axis_studio import (FullBodyRetargeter, REQUIRED, UpperBodyRetargeter,
                         local_to_gmr)
from general_motion_retargeting.utils.lafan1 import load_bvh_file
from general_motion_retargeting.utils.lafan_vendor.extract import read_bvh

BVH = Path(__file__).resolve().parents[1] / 'assets/source/sw2_1_chr01_MAYA.bvh'


class AxisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.anim = read_bvh(str(BVH))
        cls.reference, _ = load_bvh_file(str(BVH), format='nokov')

    def joints(self, frame):
        anim = self.anim
        return {name: dict(parent=None if anim.parents[i] < 0 else anim.bones[anim.parents[i]],
                           position=anim.pos[frame, i].tolist(),
                           rotation=anim.quats[frame, i].tolist())
                for i, name in enumerate(anim.bones)}

    def test_fk_matches_bvh_reference(self):
        for frame in (2, 90, 180, 450):
            converted = local_to_gmr(self.joints(frame))
            for name in self.reference[frame]:
                p, q = converted[name]
                expected_p, expected_q = self.reference[frame][name]
                np.testing.assert_allclose(p, expected_p, atol=1e-6)
                self.assertAlmostEqual(abs(np.dot(q, expected_q)), 1, places=6)

    def test_invalid_skeleton(self):
        joints = self.joints(2)
        del joints['LeftArm']
        with self.assertRaises(ValueError):
            local_to_gmr(joints)
        joints = self.joints(2)
        joints['Hips']['parent'] = 'LeftHand'
        with self.assertRaises(ValueError):
            local_to_gmr(joints)
        joints = self.joints(2)
        joints['Hips']['rotation'] = [0, 0, 0, 0]
        with self.assertRaises(ValueError):
            local_to_gmr(joints)

    def test_upper_body_with_fixed_support(self):
        runner = UpperBodyRetargeter(1.75)
        outputs = []
        for frame in range(2, 182, 3):
            pose = local_to_gmr(self.joints(frame))
            # Upper-body input works without leg or toe joints.
            pose = {name: value for name, value in pose.items() if name in REQUIRED}
            qpos = runner.step(copy.deepcopy(pose))
            self.assertTrue(np.isfinite(qpos).all())
            np.testing.assert_allclose(qpos[runner.fixed], runner.support[runner.fixed], atol=1e-8)
            outputs.append(qpos)
        self.assertGreater(float(np.max(np.ptp(outputs, axis=0))), 0.01)

    def test_full_body_tracks_legs(self):
        runner = FullBodyRetargeter(1.75)
        outputs = []
        for frame in range(2, 302, 15):
            qpos = runner.step(local_to_gmr(self.joints(frame)))
            self.assertEqual(qpos.shape, (36,))
            self.assertTrue(np.isfinite(qpos).all())
            outputs.append(qpos)
        motion = np.ptp(np.asarray(outputs), axis=0)
        # qpos 7:19 are the twelve hip, knee and ankle joints.
        self.assertGreater(float(np.max(motion[7:19])), 0.01)


if __name__ == '__main__':
    unittest.main()
