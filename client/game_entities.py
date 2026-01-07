# client/game_entities.py
from dataclasses import dataclass
import pygame
from typing import Tuple

Vec2 = pygame.math.Vector2

@dataclass
class Disc:
    id: int
    team: int     # 0=blue, 1=red, 2=ball
    pos: Vec2
    vel: Vec2
    r: int
    color: Tuple[int, int, int]

    @property
    def mass(self) -> float:
        # consistent, simple; larger discs heavier
        return float(self.r * self.r)

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.r)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.pos.x), int(self.pos.y)), self.r, 2)