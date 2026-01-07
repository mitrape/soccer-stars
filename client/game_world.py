# client/game_world.py
import pygame
from pygame.math import Vector2 as Vec2
from typing import List, Optional, Tuple

from shared.constants import WIDTH, HEIGHT, WHITE, BLACK, BLUE, RED
from shared.game_config import CFG
from client.game_entities import Disc


class GameWorld:
    """
    Phases 4+5:
      - field + discs
      - aiming / shot -> sets velocity
      - physics: friction, wall bounce, disc-disc collisions, overlap resolution
      - deterministic-ish update order
    Phase 6 uses this world by calling apply_shot() for local and remote.
    """

    def __init__(self, you_team: int, start_turn_team: int):
        self.you_team = you_team
        self.turn_team = start_turn_team

        self.discs: List[Disc] = []
        self.ball_id: int = -1
        self._spawn()

        # aim state (only used for local player input)
        self.aiming: bool = False
        self.selected_id: Optional[int] = None
        self.drag_start: Optional[Vec2] = None
        self.drag_now: Optional[Vec2] = None

    # ---------- Field ----------
    def field_rect(self) -> pygame.Rect:
        return pygame.Rect(CFG.margin, CFG.margin, WIDTH - 2 * CFG.margin, HEIGHT - 2 * CFG.margin)

    def goal_rects(self) -> Tuple[pygame.Rect, pygame.Rect]:
        f = self.field_rect()
        y1 = HEIGHT // 2 - CFG.goal_h // 2
        left = pygame.Rect(f.left - CFG.goal_depth, y1, CFG.goal_depth * 2, CFG.goal_h)
        right = pygame.Rect(f.right - CFG.goal_depth, y1, CFG.goal_depth * 2, CFG.goal_h)
        return left, right

    # ---------- Spawning ----------
    def _spawn(self):
        self.discs.clear()
        cx, cy = WIDTH / 2, HEIGHT / 2

        blue_positions = [
            (cx - 300, cy - 120),
            (cx - 300, cy + 120),
            (cx - 380, cy),
            (cx - 220, cy),
            (cx - 380, cy - 220),
        ]
        red_positions = [
            (cx + 300, cy - 120),
            (cx + 300, cy + 120),
            (cx + 380, cy),
            (cx + 220, cy),
            (cx + 380, cy + 220),
        ]

        pid = 0
        for p in blue_positions:
            self.discs.append(Disc(pid, 0, Vec2(p), Vec2(0, 0), CFG.piece_r, BLUE))
            pid += 1
        for p in red_positions:
            self.discs.append(Disc(pid, 1, Vec2(p), Vec2(0, 0), CFG.piece_r, RED))
            pid += 1

        self.ball_id = pid
        self.discs.append(Disc(pid, 2, Vec2(cx, cy), Vec2(0, 0), CFG.ball_r, WHITE))

    # ---------- State helpers ----------
    def get(self, disc_id: int) -> Optional[Disc]:
        for d in self.discs:
            if d.id == disc_id:
                return d
        return None

    def any_moving(self) -> bool:
        eps2 = CFG.stop_eps * CFG.stop_eps
        return any(d.vel.length_squared() > eps2 for d in self.discs)

    def is_my_turn(self) -> bool:
        return self.turn_team == self.you_team

    # ---------- Aiming & input (local only) ----------
    def can_shoot_now(self) -> bool:
        return self.is_my_turn() and (not self.any_moving())

    def pick_disc(self, p: Vec2) -> Optional[int]:
        if not self.can_shoot_now():
            return None
        # Only pick your pieces, never the ball
        for d in self.discs:
            if d.team == self.you_team and (d.pos - p).length() <= d.r:
                return d.id
        return None

    def on_mouse_down(self, pos) -> None:
        disc_id = self.pick_disc(Vec2(pos))
        if disc_id is None:
            return
        self.aiming = True
        self.selected_id = disc_id
        self.drag_start = Vec2(pos)
        self.drag_now = Vec2(pos)

    def on_mouse_move(self, pos) -> None:
        if self.aiming:
            self.drag_now = Vec2(pos)

    def on_mouse_up(self, pos) -> Optional[Tuple[int, float, float]]:
        """
        Returns a SHOT tuple: (piece_id, angle, power) or None.
        angle in radians, power in [0..1]
        """
        if not self.aiming or self.selected_id is None or self.drag_start is None:
            self._reset_aim()
            return None

        end = Vec2(pos)
        drag = (self.drag_start - end)  # pull back
        length = drag.length()
        if length < 6:
            self._reset_aim()
            return None

        if length > CFG.max_drag:
            drag.scale_to_length(CFG.max_drag)
            length = CFG.max_drag

        angle = float(drag.as_polar()[1])  # degrees
        angle_rad = float(angle * 3.141592653589793 / 180.0)
        power = float(length / CFG.max_drag)

        pid = self.selected_id
        self._reset_aim()
        return (pid, angle_rad, power)

    def _reset_aim(self):
        self.aiming = False
        self.selected_id = None
        self.drag_start = None
        self.drag_now = None

    # ---------- Apply shot (used by BOTH local + remote) ----------
    def apply_shot(self, piece_id: int, angle: float, power: float) -> bool:
        d = self.get(piece_id)
        if d is None:
            return False
        if d.team not in (0, 1):
            return False
        # power -> velocity magnitude
        p = max(0.0, min(1.0, float(power)))
        vmag = p * CFG.max_drag * CFG.power_scale
        d.vel = Vec2(vmag, 0).rotate_rad(angle)
        return True

    # ---------- Physics (Phase 5) ----------
    def update(self, dt: float) -> None:
        if dt <= 0:
            return

        f = self.field_rect()

        # integrate + wall collision
        for d in self.discs:
            if d.vel.length_squared() < 1e-6:
                d.vel.update(0, 0)
                continue

            d.pos += d.vel * dt

            # friction scaled to dt (reference 60fps)
            friction = CFG.friction_per_60fps ** (dt * 60.0)
            d.vel *= friction

            # walls (reflect)
            left = f.left + d.r
            right = f.right - d.r
            top = f.top + d.r
            bottom = f.bottom - d.r

            if d.pos.x < left:
                d.pos.x = left
                d.vel.x *= -CFG.wall_restitution
            elif d.pos.x > right:
                d.pos.x = right
                d.vel.x *= -CFG.wall_restitution

            if d.pos.y < top:
                d.pos.y = top
                d.vel.y *= -CFG.wall_restitution
            elif d.pos.y > bottom:
                d.pos.y = bottom
                d.vel.y *= -CFG.wall_restitution

            if d.vel.length() < CFG.stop_eps:
                d.vel.update(0, 0)

        # disc-disc collisions (pairwise)
        self._resolve_collisions()

    def _resolve_collisions(self):
        n = len(self.discs)
        e = CFG.restitution

        for i in range(n):
            a = self.discs[i]
            for j in range(i + 1, n):
                b = self.discs[j]

                delta = b.pos - a.pos
                dist = delta.length()
                min_dist = a.r + b.r

                if dist <= 0:
                    # rare perfect overlap: nudge
                    delta = Vec2(1, 0)
                    dist = 1.0

                if dist >= min_dist:
                    continue

                # overlap resolution (push apart proportionally to mass)
                overlap = min_dist - dist
                nrm = delta / dist

                ma, mb = a.mass, b.mass
                total = ma + mb
                if total <= 0:
                    total = 1.0

                a.pos -= nrm * overlap * (mb / total)
                b.pos += nrm * overlap * (ma / total)

                # relative velocity along normal
                rel = b.vel - a.vel
                vn = rel.dot(nrm)
                if vn > 0:
                    continue  # separating

                # impulse scalar
                j_imp = -(1 + e) * vn
                j_imp /= (1 / ma) + (1 / mb)

                impulse = j_imp * nrm
                a.vel -= impulse / ma
                b.vel += impulse / mb

                # small clamp to avoid jitter
                if a.vel.length() < CFG.stop_eps:
                    a.vel.update(0, 0)
                if b.vel.length() < CFG.stop_eps:
                    b.vel.update(0, 0)

    # ---------- Draw ----------
    def draw(self, surface):
        # field
        surface.fill((30, 90, 50))
        f = self.field_rect()
        pygame.draw.rect(surface, (230, 230, 230), f, 6, border_radius=14)

        # center line & circle
        pygame.draw.line(surface, (230, 230, 230), (WIDTH // 2, f.top), (WIDTH // 2, f.bottom), 4)
        pygame.draw.circle(surface, (230, 230, 230), (WIDTH // 2, HEIGHT // 2), 90, 4)

        # goals
        lg, rg = self.goal_rects()
        pygame.draw.rect(surface, (245, 245, 245), lg, 0, border_radius=8)
        pygame.draw.rect(surface, (245, 245, 245), rg, 0, border_radius=8)
        pygame.draw.rect(surface, BLACK, lg, 2, border_radius=8)
        pygame.draw.rect(surface, BLACK, rg, 2, border_radius=8)

        # discs
        for d in self.discs:
            d.draw(surface)

        # aim line
        if self.aiming and self.selected_id is not None and self.drag_now is not None:
            d = self.get(self.selected_id)
            if d:
                pygame.draw.line(surface, (255, 255, 0), (int(d.pos.x), int(d.pos.y)),
                                 (int(self.drag_now.x), int(self.drag_now.y)), 4)