from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerCommand:
    move_x: int = 0
    jump_pressed: bool = False


@dataclass(frozen=True)
class ActorPose:
    x: float
    y: float
    facing_left: bool
    velocity_y: float
    grounded: bool
