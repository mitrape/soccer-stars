# client/screens.py
import pygame
from shared.constants import WIDTH, HEIGHT, WHITE, BLACK, GRAY, DARK, BLUE, GREEN, ORANGE, RED
from client.ui import Button, TextInput
from client.game_world import GameWorld


class Screen:
    name = "base"
    def __init__(self, app): self.app = app
    def on_enter(self, **kwargs): pass
    def on_exit(self): pass
    def handle_event(self, event): pass
    def update(self, dt): pass
    def draw(self, surface): pass
    def on_network(self, msg): pass


# -------------------- Splash --------------------
class SplashScreen(Screen):
    name = "splash"
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 64)
        self.small_font = pygame.font.SysFont(None, 26)
        self.connect_btn = Button((WIDTH//2 - 160, HEIGHT//2 + 70, 320, 55),
                                  "Connect + Go to Login", self.small_font, BLUE, WHITE)
        self.status = "Not connected"

    def on_enter(self, **kwargs):
        if not self.app.net.connected:
            ok = self.app.net.connect(self.app.server_host, self.app.server_port)
            self.status = "Connected ✅" if ok else "Connect failed ❌"
        else:
            self.status = "Connected ✅"

    def handle_event(self, event):
        if self.connect_btn.is_clicked(event):
            if not self.app.net.connected:
                ok = self.app.net.connect(self.app.server_host, self.app.server_port)
                self.status = "Connected ✅" if ok else "Connect failed ❌"
            if self.app.net.connected:
                self.app.change_screen("login")

    def draw(self, surface):
        surface.fill(DARK)
        title = self.title_font.render("SOCCER STARS", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))
        st = self.small_font.render(self.status, True, GRAY)
        surface.blit(st, st.get_rect(center=(WIDTH//2, HEIGHT//2)))
        self.connect_btn.draw(surface)


# -------------------- Login --------------------
class LoginScreen(Screen):
    name = "login"
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 24)
        self.username = TextInput((WIDTH//2 - 180, 220, 360, 45), self.small_font, "Username")
        self.password = TextInput((WIDTH//2 - 180, 275, 360, 45), self.small_font, "Password", is_password=True)
        self.login_btn = Button((WIDTH//2 - 180, 345, 360, 50), "Login", self.small_font, GREEN, WHITE)
        self.goto_signup_btn = Button((WIDTH//2 - 180, 405, 360, 45),
                                      "Create account (Signup)", self.small_font, ORANGE, BLACK)
        self.msg = ""
        self.waiting_for = None

    def on_enter(self, **kwargs):
        self.msg = kwargs.get("message", "")

    def handle_event(self, event):
        self.username.handle_event(event)
        self.password.handle_event(event)

        if self.login_btn.is_clicked(event):
            if not self.app.net.connected:
                self.msg = "Not connected to server."
                return
            u = self.username.value()
            pw = self.password.value()
            if not u:
                self.msg = "Username is required."
                return
            if not pw:
                self.msg = "Password is required."
                return
            self.waiting_for = "LOGIN"
            self.app.net.send({"type": "LOGIN", "username": u, "password": pw})

        if self.goto_signup_btn.is_clicked(event):
            self.app.change_screen("signup")

    def on_network(self, msg):
        t = msg.get("type")
        if t == "OK" and self.waiting_for == "LOGIN":
            self.waiting_for = None
            self.app.me = self.username.value()
            self.app.net.send({"type": "SET_UDP_PORT", "udp_port": self.app.my_udp_port})
            self.app.change_screen("lobby")
        elif t == "ERROR":
            self.waiting_for = None
            self.msg = msg.get("message", "Error")

    def draw(self, surface):
        surface.fill((18, 24, 36))
        title = self.title_font.render("Login", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, 140)))
        self.username.draw(surface)
        self.password.draw(surface)
        self.login_btn.draw(surface)
        self.goto_signup_btn.draw(surface)
        msg = self.small_font.render(self.msg, True, GRAY)
        surface.blit(msg, (WIDTH//2 - 300, 500))


# -------------------- Signup --------------------
class SignupScreen(Screen):
    name = "signup"
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 24)
        self.username = TextInput((WIDTH//2 - 180, 200, 360, 45), self.small_font, "Username")
        self.email = TextInput((WIDTH//2 - 180, 255, 360, 45), self.small_font, "Email")
        self.password = TextInput((WIDTH//2 - 180, 310, 360, 45), self.small_font, "Password", is_password=True)
        self.signup_btn = Button((WIDTH//2 - 180, 380, 360, 50), "Signup (Register)", self.small_font, ORANGE, BLACK)
        self.back_btn = Button((WIDTH//2 - 180, 440, 360, 45), "Back to Login", self.small_font, BLUE, WHITE)
        self.msg = ""
        self.waiting_for = None

    def handle_event(self, event):
        self.username.handle_event(event)
        self.email.handle_event(event)
        self.password.handle_event(event)

        if self.back_btn.is_clicked(event):
            self.app.change_screen("login")

        if self.signup_btn.is_clicked(event):
            if not self.app.net.connected:
                self.msg = "Not connected to server."
                return
            u = self.username.value()
            e = self.email.value()
            pw = self.password.value()
            if not u:
                self.msg = "Username is required."
                return
            if not e or "@" not in e or "." not in e:
                self.msg = "Please enter a valid email."
                return
            if not pw:
                self.msg = "Password is required."
                return
            self.waiting_for = "REGISTER"
            self.msg = "Registering..."
            self.app.net.send({"type": "REGISTER", "username": u, "email": e, "password": pw})

    def on_network(self, msg):
        t = msg.get("type")
        if t == "OK" and self.waiting_for == "REGISTER":
            self.waiting_for = None
            self.app.change_screen("login", message="Signup success ✅ Now login.")
        elif t == "ERROR":
            self.waiting_for = None
            self.msg = msg.get("message", "Error")

    def draw(self, surface):
        surface.fill((16, 30, 28))
        title = self.title_font.render("Signup", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, 130)))
        self.username.draw(surface)
        self.email.draw(surface)
        self.password.draw(surface)
        self.signup_btn.draw(surface)
        self.back_btn.draw(surface)
        msg = self.small_font.render(self.msg, True, GRAY)
        surface.blit(msg, (WIDTH//2 - 300, 520))


# -------------------- Lobby --------------------
class LobbyScreen(Screen):
    name = "lobby"

    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 24)

        self.users = []
        self.timer = 0.0
        self.msg = "Click a free user to invite."

        self.incoming_from = None
        self.accept_btn = Button((WIDTH//2 - 170, HEIGHT//2 + 40, 160, 50), "Accept", self.small_font, GREEN, WHITE)
        self.decline_btn = Button((WIDTH//2 + 10,  HEIGHT//2 + 40, 160, 50), "Decline", self.small_font, RED, WHITE)

    def on_enter(self, **kwargs):
        self.timer = 0.0
        self.incoming_from = None

        # ✅ Auto-reconnect TCP if it dropped
        if not self.app.net.connected:
            ok = self.app.net.connect(self.app.server_host, self.app.server_port)
            if not ok:
                self.msg = "Not connected to server."
                return

            # after reconnect, re-identify session (simple approach):
            # your server doesn't support token sessions, so we just show message.
            # user can re-login if needed.
            self.msg = "Reconnected. If you were logged out, login again."

        # refresh list
        self.app.net.send({"type": "LIST_USERS"})
        self.msg = "Click a free user to invite."

    def handle_event(self, event):
        if self.incoming_from:
            if self.accept_btn.is_clicked(event):
                self.app.net.send({"type": "INVITE_RESPONSE", "from": self.incoming_from, "accepted": True})
                self.incoming_from = None
            elif self.decline_btn.is_clicked(event):
                self.app.net.send({"type": "INVITE_RESPONSE", "from": self.incoming_from, "accepted": False})
                self.incoming_from = None
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.app.net.connected:
                self.msg = "Not connected to server."
                return

            mx, my = event.pos
            start_y = 200
            row_h = 36
            for i, u in enumerate(self.users):
                y = start_y + i * row_h
                rect = pygame.Rect(WIDTH//2 - 200, y, 400, row_h - 4)
                if rect.collidepoint((mx, my)):
                    target = u["username"]
                    if target == self.app.me:
                        self.msg = "You cannot invite yourself."
                        return
                    if u.get("status") != "free":
                        self.msg = f"{target} is busy."
                        return
                    self.app.net.send({"type": "INVITE", "to": target})
                    self.msg = f"Invite sent to {target}..."
                    return

    def update(self, dt):
        self.timer += dt
        if self.timer >= 1.0:
            self.timer = 0.0
            if self.app.net.connected:
                self.app.net.send({"type": "LIST_USERS"})

    def on_network(self, msg):
        t = msg.get("type")
        if t == "USERS":
            self.users = msg.get("users", [])
        elif t == "INVITE_RECEIVED":
            self.incoming_from = msg.get("from")
        elif t == "INVITE_DECLINED":
            self.msg = f"Invite declined by {msg.get('by')}"
        elif t == "MATCH_START":
            self.app.match_info = msg
            self.app.change_screen("game", match=msg)
        elif t == "ERROR":
            self.msg = msg.get("message", "Error")

    def draw(self, surface):
        surface.fill((24, 40, 28))
        title = self.title_font.render("Lobby", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, 120)))

        msg = self.small_font.render(self.msg, True, GRAY)
        surface.blit(msg, (WIDTH//2 - 300, 160))

        start_y = 200
        row_h = 36
        header = self.small_font.render("Online users (click to invite):", True, WHITE)
        surface.blit(header, (WIDTH//2 - 200, start_y - 30))

        for i, u in enumerate(self.users):
            name = u["username"]
            st = u.get("status", "free")
            y = start_y + i * row_h
            rect = pygame.Rect(WIDTH//2 - 200, y, 400, row_h - 4)

            bg = (220, 220, 220) if st == "free" else (200, 200, 200)
            pygame.draw.rect(surface, bg, rect, border_radius=8)
            pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=8)

            txt = self.small_font.render(f"{name}  [{st}]", True, (10, 10, 10))
            surface.blit(txt, (rect.x + 12, rect.y + 8))

        if self.incoming_from:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            surface.blit(overlay, (0, 0))

            box = pygame.Rect(WIDTH//2 - 240, HEIGHT//2 - 120, 480, 220)
            pygame.draw.rect(surface, (245, 245, 245), box, border_radius=14)
            pygame.draw.rect(surface, (0, 0, 0), box, 2, border_radius=14)

            txt = self.small_font.render(f"Invite from: {self.incoming_from}", True, (10, 10, 10))
            surface.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 30)))

            self.accept_btn.draw(surface)
            self.decline_btn.draw(surface)

# -------------------- Game (Phases 4..8) --------------------
class GameScreen(Screen):
    name = "game"
    WIN_SCORE = 2

    def __init__(self, app):
        super().__init__(app)
        self.small_font = pygame.font.SysFont(None, 24)
        self.big_font = pygame.font.SysFont(None, 64)

        self.match = None
        self.world = None

        self.p2p_status = "Starting…"

        # turn + motion
        self.shot_in_progress = False
        self.prev_moving = False

        # fixed timestep
        self.accum = 0.0
        self.fixed_dt = 1.0 / 120.0

        # Phase 7
        self.hash_timer = 0.0
        self.local_tick = 0
        self.last_peer_hash = None
        self.last_local_hash = None
        self.snapshot_cooldown = 0.0

        # Phase 8
        self.score_blue = 0
        self.score_red = 0
        self.banner = ""
        self.banner_timer = 0.0
        self.game_over = False
        self.winner_team = None  # 0/1

        # auto-return to lobby after game over
        self.return_timer = 0.0
        self._returned = False

    def on_enter(self, **kwargs):
        self.match = kwargs.get("match")

        self.p2p_status = "Starting…"
        self.shot_in_progress = False
        self.prev_moving = False
        self.accum = 0.0

        self.hash_timer = 0.0
        self.local_tick = 0
        self.last_peer_hash = None
        self.last_local_hash = None
        self.snapshot_cooldown = 0.0

        self.score_blue = 0
        self.score_red = 0
        self.banner = ""
        self.banner_timer = 0.0
        self.game_over = False
        self.winner_team = None

        self.return_timer = 0.0
        self._returned = False

        # start UDP match
        self.app.udp_peer.begin_match(
            match_id=self.match.get("match_id"),
            peer_ip=self.match.get("peer_ip"),
            peer_port=self.match.get("peer_udp_port"),
            my_username=self.app.me,
        )

        you_team = 0 if self.match.get("you_start") else 1
        from client.game_world import GameWorld
        self.world = GameWorld(you_team=you_team, start_turn_team=0)



    # ---------- helpers ----------
    def _set_free_and_back_to_lobby(self):
        """
        Each client will call this locally.
        That makes BOTH players free because both clients run it.
        """
        if self._returned:
            return
        self._returned = True

        # tell server we are free again
        if self.app.net.connected:
            self.app.net.send({"type": "MATCH_END"})

        # go back to lobby and refresh list
        self.app.change_screen("lobby")

    # ---------- UDP handling ----------
    def _handle_udp(self, msg: dict):
        if not self.world:
            return

        t = msg.get("type")

        if t == "SHOT":
            piece_id = int(msg.get("piece"))
            angle = float(msg.get("angle"))
            power = float(msg.get("power"))
            ok = self.world.apply_shot(piece_id, angle, power)
            if ok:
                self.shot_in_progress = True

        # Phase 7
        elif t == "STATE_HASH":
            self.last_peer_hash = msg.get("hash")

            if (not self.world.any_moving()) and self.last_local_hash and self.last_peer_hash:
                if self.last_local_hash != self.last_peer_hash and self.snapshot_cooldown <= 0.0:
                    self.app.udp_peer.send_snapshot_req(self.local_tick)
                    self.snapshot_cooldown = 0.7

        elif t == "SNAPSHOT_REQ":
            if not self.world.any_moving():
                snap = self.world.make_snapshot()
                self.app.udp_peer.send_snapshot(int(msg.get("tick", 0)), snap)

        elif t == "STATE_SNAPSHOT":
            snap = msg.get("state")
            if isinstance(snap, dict):
                self.world.apply_snapshot_soft(snap, pos_threshold=6.0)

        # Phase 8
        elif t == "GOAL":
            scorer = int(msg.get("scorer"))
            self.score_blue = int(msg.get("score_blue", self.score_blue))
            self.score_red = int(msg.get("score_red", self.score_red))
            self.banner = "GOAL! " + ("BLUE" if scorer == 0 else "RED")
            self.banner_timer = 1.4

        elif t == "RESET":
            payload = msg.get("payload")
            if isinstance(payload, dict):
                self.world.import_positions(payload)
                self.shot_in_progress = False
                self.prev_moving = False

        elif t == "END":
            # show end overlay, then auto return to lobby
            self.game_over = True
            self.winner_team = int(msg.get("winner"))
            self.score_blue = int(msg.get("score_blue", self.score_blue))
            self.score_red = int(msg.get("score_red", self.score_red))
            self.return_timer = 2.0  # show winner 2 seconds then go lobby

    # ---------- Input ----------
    def handle_event(self, event):
        if not self.world:
            return

        # allow ESC immediate exit still (your global handler will stop app)

        if self.game_over:
            # ignore mouse controls after game over
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.world.on_mouse_down(event.pos)

        elif event.type == pygame.MOUSEMOTION:
            self.world.on_mouse_move(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            shot = self.world.on_mouse_up(event.pos)
            if shot and self.world.can_shoot_now():
                piece_id, angle, power = shot
                ok = self.world.apply_shot(piece_id, angle, power)
                if ok:
                    self.app.udp_peer.send_shot(piece_id, angle, power)
                    self.shot_in_progress = True

    # ---------- Update ----------
    def update(self, dt):
        self.p2p_status = "P2P connected ✅" if self.app.udp_peer.connected else self.app.udp_peer.status_text

        # pump UDP inbox
        for m in self.app.udp_peer.poll():
            self._handle_udp(m)

        if not self.world:
            return

        if self.snapshot_cooldown > 0.0:
            self.snapshot_cooldown -= dt

        if self.banner_timer > 0.0:
            self.banner_timer -= dt
            if self.banner_timer <= 0:
                self.banner = ""

        # fixed timestep physics
        self.accum += dt
        if self.accum > 0.25:
            self.accum = 0.25

        while self.accum >= self.fixed_dt:
            if not self.game_over:
                self.world.update(self.fixed_dt)
            self.accum -= self.fixed_dt

        moving = self.world.any_moving()

        # turn switching after a shot ends
        if (not self.game_over) and self.shot_in_progress and self.prev_moving and (not moving):
            self.world.turn_team = 1 - self.world.turn_team
            self.shot_in_progress = False

        self.prev_moving = moving

        # Phase 8: local goal detection (only while playing)
        if not self.game_over:
            scorer = self.world.check_goal()
            if scorer is not None:
                if scorer == 0:
                    self.score_blue += 1
                else:
                    self.score_red += 1

                self.banner = "GOAL! " + ("BLUE" if scorer == 0 else "RED")
                self.banner_timer = 1.4
                self.app.udp_peer.send_goal(scorer, self.score_blue, self.score_red)

                # win condition
                if self.score_blue >= self.WIN_SCORE or self.score_red >= self.WIN_SCORE:
                    winner = 0 if self.score_blue > self.score_red else 1
                    self.game_over = True
                    self.winner_team = winner
                    self.return_timer = 2.0
                    self.app.udp_peer.send_end(winner, self.score_blue, self.score_red)
                    return

                # reset for next kickoff; scoring team starts
                next_turn = scorer
                from client.game_world import GameWorld
                you_team = self.world.you_team
                self.world = GameWorld(you_team=you_team, start_turn_team=next_turn)

                payload = self.world.export_positions()
                self.app.udp_peer.send_reset(payload)

                self.shot_in_progress = False
                self.prev_moving = False

        # Phase 7: send hash every 1s only between turns
        self.hash_timer += dt
        if self.hash_timer >= 1.0:
            self.hash_timer = 0.0
            self.local_tick += 1

            if (not self.game_over) and (not self.world.any_moving()):
                self.last_local_hash = self.world.state_hash()
                self.app.udp_peer.send_state_hash(self.local_tick, self.last_local_hash)

        # auto return after end
        if self.game_over and self.return_timer > 0.0:
            self.return_timer -= dt
            if self.return_timer <= 0.0:
                self._set_free_and_back_to_lobby()

    # ---------- Draw ----------
    def draw(self, surface):
        if not self.world:
            surface.fill((20, 20, 20))
            return

        self.world.draw(surface)

        turn_txt = "YOU" if self.world.turn_team == self.world.you_team else "OPPONENT"
        hud = [
            f"p2p: {self.p2p_status}",
            f"score: BLUE {self.score_blue}  -  RED {self.score_red}",
            f"turn: {turn_txt}",
        ]
        y = 10
        for line in hud:
            surface.blit(self.small_font.render(line, True, WHITE), (10, y))
            y += 22

        if self.banner:
            img = self.big_font.render(self.banner, True, WHITE)
            surface.blit(img, img.get_rect(center=(WIDTH // 2, 70)))

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            surface.blit(overlay, (0, 0))

            winner_txt = "BLUE WINS!" if self.winner_team == 0 else "RED WINS!"
            img = self.big_font.render(winner_txt, True, WHITE)
            surface.blit(img, img.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))

            small = self.small_font.render("Returning to Lobby…", True, WHITE)
            surface.blit(small, small.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))