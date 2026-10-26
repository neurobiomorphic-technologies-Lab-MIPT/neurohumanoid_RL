"""Timestamped G1 trajectories with a flushed recovery journal."""
import json
import os
import tempfile
from pathlib import Path

import numpy as np


def save_trajectory(path, timestamps, qpos, joint_names, metadata):
    path = Path(path)
    timestamps = np.asarray(timestamps, dtype=float)
    qpos = np.asarray(qpos, dtype=float)
    if (not len(timestamps) or qpos.shape != (len(timestamps), 36) or
            len(joint_names) != 29 or not np.isfinite(qpos).all() or
            not np.isfinite(timestamps).all() or np.any(np.diff(timestamps) <= 0)):
        raise ValueError('Invalid trajectory dimensions, values or timestamps')
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.npz', delete=False) as f:
            temp = Path(f.name)
            np.savez_compressed(f, timestamps_s=timestamps, qpos=qpos,
                                root_pos=qpos[:, :3], root_rot_wxyz=qpos[:, 3:7],
                                joint_pos=qpos[:, 7:], joint_names=np.asarray(joint_names),
                                metadata_json=json.dumps(metadata), schema_version=1)
            f.flush()
            os.fsync(f.fileno())
        # Publish without overwriting an existing take, including concurrent writers.
        os.link(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


class TrajectoryRecorder:
    def __init__(self, path, joint_names, metadata):
        self.path = Path(path)
        if self.path.suffix != '.npz':
            raise ValueError('--record must end with .npz')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError(self.path)
        self.journal = self.path.with_suffix('.npz.partial')
        self.stream = self.journal.open('x')
        self.joint_names = joint_names
        self.metadata = metadata
        self.timestamps = []
        self.qpos = []
        self.stream.write(json.dumps(dict(joint_names=joint_names, metadata=metadata)) + '\n')
        self.stream.flush()

    def append(self, timestamp, qpos):
        qpos = np.asarray(qpos, dtype=float).copy()
        if qpos.shape != (36,) or not np.isfinite(qpos).all() or not np.isfinite(timestamp):
            raise ValueError('Invalid recorded pose')
        if self.timestamps and timestamp <= self.timestamps[-1]:
            raise ValueError('Recording timestamps must increase')
        self.stream.write(json.dumps(dict(t=timestamp, qpos=qpos.tolist())) + '\n')
        self.stream.flush()
        self.timestamps.append(timestamp)
        self.qpos.append(qpos)

    def close(self):
        if self.stream.closed:
            return
        self.stream.close()
        if self.timestamps:
            save_trajectory(self.path, self.timestamps, self.qpos, self.joint_names, self.metadata)
            print(f'Trajectory saved: {self.path} ({len(self.timestamps)} frames)', flush=True)
        else:
            print('No poses received; no trajectory saved.', flush=True)
        self.journal.unlink()


def recover_trajectory(journal, output):
    """Recover complete flushed frames after a process crash or forced shutdown."""
    with Path(journal).open() as f:
        header = json.loads(next(f))
        frames = []
        for line in f:
            try:
                frames.append(json.loads(line))
            except json.JSONDecodeError:
                if f.read().strip():
                    raise ValueError('Corrupt journal before its final line')
                break
    save_trajectory(output, [frame['t'] for frame in frames],
                    [frame['qpos'] for frame in frames],
                    header['joint_names'], header['metadata'])
