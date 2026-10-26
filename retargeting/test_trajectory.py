import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from trajectory import TrajectoryRecorder, recover_trajectory


class RecordingTests(unittest.TestCase):
    def test_save_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'take.npz'
            recorder = TrajectoryRecorder(path, [f'joint_{i}' for i in range(29)], {'test': True})
            pose = np.zeros(36)
            pose[3] = 1
            recorder.append(0.1, pose)
            pose[7] = 0.5
            recorder.append(0.3, pose)
            recorder.close()
            recorder.close()
            with np.load(path, allow_pickle=False) as data:
                np.testing.assert_allclose(data['timestamps_s'], [0.1, 0.3])
                np.testing.assert_allclose(data['joint_pos'][:, 0], [0, 0.5])
                self.assertEqual(data['root_rot_wxyz'].shape, (2, 4))
                self.assertTrue(json.loads(str(data['metadata_json']))['test'])
            self.assertFalse(recorder.journal.exists())
            with self.assertRaises(FileExistsError):
                TrajectoryRecorder(path, [], {})

    def test_recover_incomplete_final_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'take.npz'
            recorder = TrajectoryRecorder(path, [f'joint_{i}' for i in range(29)], {})
            recorder.append(1, np.r_[np.zeros(3), 1, np.zeros(32)])
            recorder.stream.write('{"t":')
            recorder.stream.close()
            recover_trajectory(recorder.journal, path)
            with np.load(path, allow_pickle=False) as data:
                self.assertEqual(data['qpos'].shape, (1, 36))

    def test_no_input_and_nonmonotonic_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'empty.npz'
            recorder = TrajectoryRecorder(path, ['joint'] * 29, {})
            recorder.close()
            self.assertFalse(path.exists())
            recorder = TrajectoryRecorder(path, ['joint'] * 29, {})
            recorder.append(1, np.r_[np.zeros(3), 1, np.zeros(32)])
            with self.assertRaises(ValueError):
                recorder.append(1, np.zeros(36))
            recorder.close()


if __name__ == '__main__':
    unittest.main()
