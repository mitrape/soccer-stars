# shared/game_config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class GameConfig:
    margin: int = 60

    goal_h: int = 180
    goal_depth: int = 18  # visual

    piece_r: int = 22
    ball_r: int = 14

    max_drag: int = 150          # pixels
    power_scale: float = 12.0    # velocity multiplier

    friction_per_60fps: float = 0.985
    stop_eps: float = 10.0       # px/s

    restitution: float = 0.92    # bounciness for disc collisions
    wall_restitution: float = 0.85

CFG = GameConfig()