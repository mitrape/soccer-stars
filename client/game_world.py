# client/game_world.py
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

import pygame
from pygame.math import Vector2 as Vec2

from shared.constants import WIDTH, HEIGHT, WHITE, BLACK, BLUE, RED


# ---------------- Configuration ----------------
@dataclass
class WorldCfg:
    margin: int = 40

    piece_r: int = 22
    ball_r: int = 14

    wall_restitution: float = 0.85
    restitution: float = 0.90

    # friction: multiply vel by friction_per_60fps each 1/60s
    friction_per_60fps: float = 0.985

    # stop condition
    stop_eps: float = 8.0           # px/sec threshold
    sleep_frames: int = 8           # consecutive frames below eps to become stopped

    # input
    max_drag: float = 120.0
    power_scale: float = 7.0        # speed = power * max_drag * power_scale


CFG = WorldCfg()


# ---------------- Entity ----------------
@dataclass
class Disc:
    id: int
    team: int            # 0 blue, 1 red, 2 ball
    pos: Vec2
    vel: Vec2
    r: float
    color: Tuple[int, int, int]
    mass: float

    def draw(self, surf: pygame.Surface):
        pygame.draw.circle(surf, self.color, (int(self.pos.x), int(self.pos.y)), int(self.r))
        pygame.draw.circle(surf, BLACK, (int(self.pos.x), int(self.pos.y)), int(self.r), 2)


# ---------------- World ----------------
class GameWorld:
    """
    Local physics world.
    Sync rule: only SHOT input is sent; both sides simulate locally.

    Phase 7: hash/snapshot correction is allowed ONLY when stopped (between turns).
    """

    def __init__(self, you_team: int, start_turn_team: int = 0):
        self.you_team = int(you_team)
        self.turn_team = int(start_turn_team)

        self.discs: List[Disc] = []
        self.ball_id: int = -1

        # aiming state
        self.aiming: bool = False
        self.selected_id: Optional[int] = None
        self.drag_now: Optional[Vec2] = None

        # robust stop logic
        # IMPORTANT: Start as already "settled" so first move works immediately.
        self._below_eps_frames: int = CFG.sleep_frames
        self._ever_moved: bool = False

        # Phase 7 soft correction targets (positions only)
        self._corr_targets: Dict[int, Vec2] = {}
        self._corr_active: bool = False

        self._spawn()

    # ---------------- Layout ----------------
    def field_rect(self) -> pygame.Rect:
        return pygame.Rect(CFG.margin, CFG.margin, WIDTH - 2 * CFG.margin, HEIGHT - 2 * CFG.margin)

    def _spawn(self):
        self.discs.clear()
        f = self.field_rect()
        cx, cy = f.centerx, f.centery

        blue_positions = [
            (cx - 260, cy - 110),
            (cx - 260, cy + 110),
            (cx - 340, cy),
            (cx - 180, cy),
            (cx - 340, cy - 220),
        ]
        red_positions = [
            (cx + 260, cy - 110),
            (cx + 260, cy + 110),
            (cx + 340, cy),
            (cx + 180, cy),
            (cx + 340, cy + 220),
        ]

        pid = 0
        for x, y in blue_positions:
            self.discs.append(Disc(pid, 0, Vec2(x, y), Vec2(0, 0), CFG.piece_r, BLUE, mass=2.0))
            pid += 1

        for x, y in red_positions:
            self.discs.append(Disc(pid, 1, Vec2(x, y), Vec2(0, 0), CFG.piece_r, RED, mass=2.0))
            pid += 1

        self.ball_id = pid
        self.discs.append(Disc(pid, 2, Vec2(cx, cy), Vec2(0, 0), CFG.ball_r, WHITE, mass=1.0))

    def get(self, disc_id: int) -> Optional[Disc]:
        for d in self.discs:
            if d.id == disc_id:
                return d
        return None

    # ---------------- Turn / input rules ----------------
    def is_my_turn(self) -> bool:
        return self.turn_team == self.you_team

    def can_shoot_now(self) -> bool:
        return self.is_my_turn() and (not self.any_moving())

    # ---------------- Moving detection (FIXED) ----------------
    def any_moving(self) -> bool:
        """
        Robust stopping:
        - clamp tiny velocities to zero
        - at the very beginning (before any move), allow immediate play
        - after a move happened, require sleep_frames stable frames below stop_eps
        """
        eps2 = CFG.stop_eps * CFG.stop_eps
        any_fast = False

        for d in self.discs:
            if d.vel.length_squared() <= eps2:
                d.vel.update(0, 0)
            else:
                any_fast = True

        if any_fast:
            self._ever_moved = True
            self._below_eps_frames = 0
            return True

        # none are fast now
        if not self._ever_moved:
            # initial state -> treat as stopped
            self._below_eps_frames = CFG.sleep_frames
            return False

        self._below_eps_frames += 1
        return self._below_eps_frames < CFG.sleep_frames

    # ---------------- Aiming UI ----------------
    def _pick_disc(self, p: Vec2) -> Optional[int]:
        if not self.can_shoot_now():
            return None
        for d in self.discs:
            if d.team == self.you_team and (d.pos - p).length() <= d.r:
                return d.id
        return None

    def on_mouse_down(self, pos):
        did = self._pick_disc(Vec2(pos))
        if did is None:
            return
        self.aiming = True
        self.selected_id = did
        self.drag_now = Vec2(pos)

    def on_mouse_move(self, pos):
        if self.aiming:
            self.drag_now = Vec2(pos)

    def on_mouse_up(self, pos) -> Optional[Tuple[int, float, float]]:
        if not self.aiming or self.selected_id is None:
            self._reset_aim()
            return None

        d = self.get(self.selected_id)
        if not d:
            self._reset_aim()
            return None

        end = Vec2(pos)
        drag = d.pos - end
        dist = drag.length()

        if dist < 6:
            self._reset_aim()
            return None

        if dist > CFG.max_drag:
            drag.scale_to_length(CFG.max_drag)
            dist = CFG.max_drag

        angle_rad = drag.as_polar()[1] * 3.141592653589793 / 180.0
        power = dist / CFG.max_drag

        pid = self.selected_id
        self._reset_aim()
        return pid, float(angle_rad), float(power)

    def _reset_aim(self):
        self.aiming = False
        self.selected_id = None
        self.drag_now = None

    # ---------------- Apply shot ----------------
    def apply_shot(self, piece_id: int, angle: float, power: float) -> bool:
        d = self.get(int(piece_id))
        if not d:
            return False
        if d.team not in (0, 1):
            return False

        p = max(0.0, min(1.0, float(power)))
        speed = p * CFG.max_drag * CFG.power_scale
        d.vel = Vec2(speed, 0).rotate_rad(float(angle))

        # motion starts
        self._ever_moved = True
        self._below_eps_frames = 0
        return True

    # ---------------- Physics update ----------------
    def update(self, dt: float):
        if dt <= 0:
            return

        # Phase 7 correction only between turns (stopped)
        self._step_soft_correction()

        f = self.field_rect()

        # integrate + friction + walls
        for d in self.discs:
            if d.vel.length_squared() > 0:
                d.pos += d.vel * dt

            if d.vel.length_squared() > 0:
                fr = CFG.friction_per_60fps ** (dt * 60.0)
                d.vel *= fr

            if d.vel.length() < CFG.stop_eps:
                d.vel.update(0, 0)

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

        self._resolve_collisions()

    def _resolve_collisions(self):
        n = len(self.discs)
        e = CFG.restitution
        collided = False

        for i in range(n):
            a = self.discs[i]
            for j in range(i + 1, n):
                b = self.discs[j]

                delta = b.pos - a.pos
                dist = delta.length()
                min_dist = a.r + b.r

                if dist == 0:
                    delta = Vec2(1, 0)
                    dist = 1.0

                if dist >= min_dist:
                    continue

                collided = True
                nrm = delta / dist
                overlap = min_dist - dist

                ma, mb = a.mass, b.mass
                inv_ma = 1.0 / ma
                inv_mb = 1.0 / mb
                inv_sum = inv_ma + inv_mb

                a.pos -= nrm * overlap * (inv_ma / inv_sum)
                b.pos += nrm * overlap * (inv_mb / inv_sum)

                rel = b.vel - a.vel
                vn = rel.dot(nrm)
                if vn > 0:
                    continue

                j_imp = -(1 + e) * vn / inv_sum
                impulse = j_imp * nrm

                a.vel -= impulse * inv_ma
                b.vel += impulse * inv_mb

                if a.vel.length() < CFG.stop_eps:
                    a.vel.update(0, 0)
                if b.vel.length() < CFG.stop_eps:
                    b.vel.update(0, 0)

        if collided:
            self._ever_moved = True
            self._below_eps_frames = 0

    # =========================================================
    # Phase 7 — Desync protection
    # =========================================================
    def state_hash(self) -> str:
        discs_sorted = sorted(self.discs, key=lambda d: d.id)
        parts = [f"{int(round(d.pos.x))},{int(round(d.pos.y))}" for d in discs_sorted]
        payload = (";".join(parts)).encode("utf-8")
        return hashlib.md5(payload).hexdigest()

    def make_snapshot(self) -> Dict[str, Any]:
        discs_sorted = sorted(self.discs, key=lambda d: d.id)
        discs = []
        for d in discs_sorted:
            discs.append({
                "id": d.id,
                "x": int(round(d.pos.x)),
                "y": int(round(d.pos.y)),
                "vx": float(round(d.vel.x, 3)),
                "vy": float(round(d.vel.y, 3)),
            })
        return {"discs": discs, "turn_team": int(self.turn_team)}

    def apply_snapshot_soft(self, snap: Dict[str, Any], pos_threshold: float = 6.0):
        # Only correct between turns
        if self.any_moving():
            return

        discs = snap.get("discs", [])
        if not isinstance(discs, list):
            return

        targets: Dict[int, Vec2] = {}
        for item in discs:
            try:
                did = int(item["id"])
                tx = float(item["x"])
                ty = float(item["y"])
            except Exception:
                continue

            d = self.get(did)
            if not d:
                continue

            tpos = Vec2(tx, ty)
            if (d.pos - tpos).length() >= pos_threshold:
                targets[did] = tpos

        if targets:
            self._corr_targets = targets
            self._corr_active = True

        # sync turn only between turns
        try:
            self.turn_team = int(snap.get("turn_team", self.turn_team))
        except Exception:
            pass

    def _step_soft_correction(self):
        if not self._corr_active or not self._corr_targets:
            return
        if self.any_moving():
            return

        alpha = 0.22
        done = []
        for did, tpos in self._corr_targets.items():
            d = self.get(did)
            if not d:
                done.append(did)
                continue
            d.pos = d.pos.lerp(tpos, alpha)
            d.vel.update(0, 0)
            if (d.pos - tpos).length() < 0.8:
                d.pos = tpos
                done.append(did)

        for did in done:
            self._corr_targets.pop(did, None)
        if not self._corr_targets:
            self._corr_active = False

    # ---------------- Draw ----------------
    def draw(self, surface: pygame.Surface):
        surface.fill((30, 90, 50))
        f = self.field_rect()
        pygame.draw.rect(surface, (235, 235, 235), f, 6, border_radius=14)
        pygame.draw.line(surface, (235, 235, 235), (f.centerx, f.top), (f.centerx, f.bottom), 4)
        pygame.draw.circle(surface, (235, 235, 235), (f.centerx, f.centery), 90, 4)

        for d in self.discs:
            d.draw(surface)

        if self.aiming and self.selected_id is not None and self.drag_now is not None:
            d = self.get(self.selected_id)
            if d:
                pygame.draw.line(
                    surface, (255, 255, 0),
                    (int(d.pos.x), int(d.pos.y)),
                    (int(self.drag_now.x), int(self.drag_now.y)),
                    4
                )