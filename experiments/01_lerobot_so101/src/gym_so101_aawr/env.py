"""Headless-friendly SO-101 cube-lift task backed by MuJoCo."""

from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np


class SO101LiftEnv(gym.Env):
    """Lift a randomized cube using normalized joint-delta commands.

    The RGB observation is suitable for the actor. ``state`` intentionally
    contains simulator-only object state for AAWR's privileged critic.
    """

    metadata = {"render_modes": ["rgb_array"], "render_fps": 20}
    JOINT_NAMES = (
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    )

    def __init__(
        self,
        scene_path: str | Path,
        render_mode: str = "rgb_array",
        image_size: int = 84,
        camera_name: str = "front",
        max_episode_steps: int = 140,
        control_hz: int = 20,
        reset_profiles_path: str | Path | None = None,
    ) -> None:
        super().__init__()
        if render_mode != "rgb_array":
            raise ValueError("SO101LiftEnv currently supports render_mode='rgb_array' only")
        self.scene_path = Path(scene_path).expanduser().resolve()
        if not self.scene_path.is_file():
            raise FileNotFoundError(f"SO-101 scene not found: {self.scene_path}")

        self.render_mode = render_mode
        self.image_size = image_size
        self.camera_name = camera_name
        self.max_episode_steps = max_episode_steps
        self.model = mujoco.MjModel.from_xml_path(str(self.scene_path))
        # Match SimStudio's validated 360 Hz physics setup.
        self.model.opt.timestep = 1.0 / 360.0
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=image_size, width=image_size)
        self.video_renderers: dict[tuple[int, int], mujoco.Renderer] = {}
        self.physics_steps = max(1, round(1.0 / (control_hz * self.model.opt.timestep)))

        self.joint_ids = np.array(
            [mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in self.JOINT_NAMES]
        )
        self.qpos_ids = self.model.jnt_qposadr[self.joint_ids]
        self.dof_ids = self.model.jnt_dofadr[self.joint_ids]
        self.actuator_ids = np.array(
            [mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name) for name in self.JOINT_NAMES]
        )
        self.block_joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, "block")
        self.block_qpos_id = int(self.model.jnt_qposadr[self.block_joint_id])
        self.block_dof_id = int(self.model.jnt_dofadr[self.block_joint_id])
        self.ee_site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, "gripperframe")
        self.ctrl_low = self.model.actuator_ctrlrange[self.actuator_ids, 0].astype(np.float32)
        self.ctrl_high = self.model.actuator_ctrlrange[self.actuator_ids, 1].astype(np.float32)
        self.action_scale = np.array([0.10, 0.10, 0.10, 0.12, 0.15, 0.20], dtype=np.float32)
        self.home = np.array([0.0, -0.3, 0.6, 1.2, 0.0, 1.1], dtype=np.float32)
        self.reset_profiles = None
        if reset_profiles_path is not None:
            profiles_path = Path(reset_profiles_path).expanduser().resolve()
            if not profiles_path.is_file():
                raise FileNotFoundError(f"SO-101 reset profiles not found: {profiles_path}")
            self.reset_profiles = np.load(profiles_path, allow_pickle=False)

        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(6,), dtype=np.float32)
        self.observation_space = gym.spaces.Dict(
            {
                "rgb": gym.spaces.Box(0, 255, shape=(image_size, image_size, 3), dtype=np.uint8),
                "state": gym.spaces.Box(-1e6, 1e6, shape=(34,), dtype=np.float32),
            }
        )
        self._step = 0
        self._last_frame: np.ndarray | None = None
        self._expert_block_xy = np.zeros(2, dtype=np.float64)
        self._expert_phase = 0
        self._expert_phase_steps = 0

    def _set_block(self) -> None:
        x = self.np_random.uniform(0.27, 0.33)
        y = self.np_random.uniform(0.17, 0.23)
        self.data.qpos[self.block_qpos_id : self.block_qpos_id + 7] = [x, y, 0.015, 1, 0, 0, 0]
        self.data.qvel[self.block_dof_id : self.block_dof_id + 6] = 0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        if self.reset_profiles is None:
            self.data.qpos[self.qpos_ids] = self.home
            self.data.ctrl[self.actuator_ids] = self.home
            self._set_block()
        else:
            requested = None if options is None else options.get("profile_index")
            profile_index = (
                int(self.np_random.integers(len(self.reset_profiles["qpos"])))
                if requested is None
                else int(requested)
            )
            self.data.qpos[self.qpos_ids] = self.reset_profiles["qpos"][profile_index]
            self.data.qvel[self.dof_ids] = self.reset_profiles["qvel"][profile_index]
            self.data.ctrl[self.actuator_ids] = self.reset_profiles["ctrl"][profile_index]
            cube_xy = self.reset_profiles["cube_xy"][profile_index]
            self.data.qpos[self.block_qpos_id : self.block_qpos_id + 7] = [
                cube_xy[0], cube_xy[1], 0.0125, 1, 0, 0, 0
            ]
            self.data.qvel[self.block_dof_id : self.block_dof_id + 6] = 0
        self._expert_block_xy = self.data.qpos[self.block_qpos_id : self.block_qpos_id + 2].copy()
        mujoco.mj_forward(self.model, self.data)
        if self.reset_profiles is None:
            for _ in range(max(1, round(0.2 / self.model.opt.timestep))):
                mujoco.mj_step(self.model, self.data)
        self._step = 0
        self._expert_phase = 0
        self._expert_phase_steps = 0
        obs = self._observation()
        return obs, self._info()

    def step(self, action: np.ndarray):
        action = np.asarray(action, dtype=np.float32)
        if action.shape != self.action_space.shape:
            raise ValueError(f"Expected action shape {self.action_space.shape}, got {action.shape}")
        target = self.data.ctrl[self.actuator_ids] + np.clip(action, -1, 1) * self.action_scale
        self.data.ctrl[self.actuator_ids] = np.clip(target, self.ctrl_low, self.ctrl_high)
        for _ in range(self.physics_steps):
            mujoco.mj_step(self.model, self.data)

        self._step += 1
        info = self._info()
        terminated = bool(info["is_success"])
        truncated = self._step >= self.max_episode_steps
        reward = float(terminated)
        return self._observation(), reward, terminated, truncated, info

    def _info(self) -> dict[str, float | bool]:
        block_z = float(self.data.qpos[self.block_qpos_id + 2])
        success = block_z >= 0.08
        return {"is_success": success, "success": success, "block_height": block_z}

    def _observation(self) -> dict[str, np.ndarray]:
        mujoco.mj_forward(self.model, self.data)
        qpos = self.data.qpos[self.qpos_ids]
        qvel = self.data.qvel[self.dof_ids]
        block_pose = self.data.qpos[self.block_qpos_id : self.block_qpos_id + 7]
        block_vel = self.data.qvel[self.block_dof_id : self.block_dof_id + 6]
        ee_pos = self.data.site_xpos[self.ee_site_id]
        state = np.concatenate([qpos, qvel, ee_pos, block_pose, block_vel, self.data.ctrl[self.actuator_ids]])
        self.renderer.update_scene(self.data, camera=self.camera_name)
        self._last_frame = self.renderer.render().astype(np.uint8)
        return {"rgb": self._last_frame.copy(), "state": state.astype(np.float32)}

    def expert_action(self) -> np.ndarray:
        """Deterministic Cartesian waypoint controller expressed as joint deltas."""
        grasp_xy = self._expert_block_xy + np.array([-0.005, -0.02])
        high_target = np.array([grasp_xy[0], grasp_xy[1], 0.12])
        low_target = np.array([grasp_xy[0], grasp_xy[1], 0.006])
        ee_pos = self.data.site_xpos[self.ee_site_id]

        if self._expert_phase == 0 and np.linalg.norm(ee_pos - high_target) < 0.006:
            self._expert_phase = 1
            self._expert_phase_steps = 0
        elif (
            self._expert_phase == 1
            and self._expert_phase_steps >= 28
            and np.linalg.norm(ee_pos - low_target) < 0.006
        ):
            self._expert_phase = 2
            self._expert_phase_steps = 0
        elif self._expert_phase == 2 and self._expert_phase_steps >= 16:
            self._expert_phase = 3
            self._expert_phase_steps = 0

        if self._expert_phase == 0:
            target = high_target
            gripper = 1.1
        elif self._expert_phase == 1:
            target = low_target.copy()
            target[2] = max(low_target[2], high_target[2] - 0.004 * self._expert_phase_steps)
            gripper = 1.1
        elif self._expert_phase == 2:
            target = low_target
            gripper = -0.12
        else:
            target = np.array([grasp_xy[0], grasp_xy[1], 0.14])
            gripper = -0.12
        self._expert_phase_steps += 1

        jac_pos = np.zeros((3, self.model.nv))
        jac_rot = np.zeros((3, self.model.nv))
        mujoco.mj_jacSite(self.model, self.data, jac_pos, jac_rot, self.ee_site_id)
        arm_dofs = self.dof_ids[:4]
        jac = jac_pos[:, arm_dofs]
        error = target - self.data.site_xpos[self.ee_site_id]
        delta = jac.T @ np.linalg.solve(jac @ jac.T + 1e-3 * np.eye(3), 0.3 * error)
        desired = self.data.ctrl[self.actuator_ids].copy()
        desired[:4] += np.clip(delta, -self.action_scale[:4], self.action_scale[:4])
        desired[4] = 0.0
        desired[5] = gripper
        return np.clip((desired - self.data.ctrl[self.actuator_ids]) / self.action_scale, -1, 1).astype(np.float32)

    def render(self, *, height: int | None = None, width: int | None = None, **_kwargs):
        height = self.image_size if height is None else int(height)
        width = self.image_size if width is None else int(width)
        if height == self.image_size and width == self.image_size:
            if self._last_frame is None:
                self._observation()
            return self._last_frame.copy()

        key = (height, width)
        renderer = self.video_renderers.get(key)
        if renderer is None:
            renderer = mujoco.Renderer(self.model, height=height, width=width)
            self.video_renderers[key] = renderer
        renderer.update_scene(self.data, camera=self.camera_name)
        return renderer.render().astype(np.uint8)

    def close(self) -> None:
        self.renderer.close()
        for renderer in self.video_renderers.values():
            renderer.close()
