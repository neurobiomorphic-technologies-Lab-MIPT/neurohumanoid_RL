"""SO-101 environments used by the AAWR experiments."""

from gymnasium.envs.registration import register

register(
    id="gym_so101_aawr/SO101Lift-v0",
    entry_point="gym_so101_aawr.env:SO101LiftEnv",
)

from gym_so101_aawr.env import SO101LiftEnv  # noqa: E402, F401
