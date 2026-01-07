import pygame
from shared.constants import WIDTH, HEIGHT, WHITE, BLACK, GRAY, DARK, BLUE, GREEN, ORANGE, RED
from client.ui import Button, TextInput


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
        self.connect_btn = Button((WIDTH//2 - 160, HEIGHT//2 + 70, 320, 55), "Connect + Go to Login", self.small_font, BLUE, WHITE)
        self.status = "Not connected"

    def on_enter(self, **kwargs):
        # Try connect automatically
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
        self.goto_signup_btn = Button((WIDTH//2 - 180, 405, 360, 45), "Create account (Signup)", self.small_font, ORANGE, BLACK)

        self.msg = ""
        self.waiting_for = None  # "LOGIN" or None

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

            # tell server our UDP port
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
        self.waiting_for = None  # "REGISTER" or None

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

            # ✅ Client-side validation (this was missing/broken for you)
            if not u:
                self.msg = "Username is required."
                return
            if not e:
                self.msg = "Email is required for signup."
                return
            if "@" not in e or "." not in e:
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
            # ✅ go back to login after success
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
        self.app.net.send({"type": "LIST_USERS"})

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


# -------------------- Game --------------------
class GameScreen(Screen):
    name = "game"
    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 24)
        self.match = None
        self.status = "Starting P2P…"

    def on_enter(self, **kwargs):
        self.match = kwargs.get("match")
        self.status = "Starting P2P…"

        # Start UDP P2P handshake (Phase 3)
        if self.match:
            try:
                self.app.udp_peer.begin_match(
                    match_id=self.match.get("match_id"),
                    peer_ip=self.match.get("peer_ip"),
                    peer_port=self.match.get("peer_udp_port"),
                    my_username=self.app.me,
                )
            except Exception as e:
                self.status = f"UDP init error: {e}"

    def update(self, dt):
        # Live status update
        if self.app.udp_peer.connected:
            self.status = "P2P connected ✅"
        else:
            self.status = self.app.udp_peer.status_text

    def draw(self, surface):
        surface.fill((40, 24, 24))
        title = self.title_font.render("Game Screen (Phase 3 ✅)", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, 120)))

        if self.match:
            lines = [
                f"match_id: {self.match.get('match_id')}",
                f"peer: {self.match.get('peer_username')}",
                f"peer_ip: {self.match.get('peer_ip')}  peer_udp_port: {self.match.get('peer_udp_port')}",
                f"you_start: {self.match.get('you_start')}",
                f"udp_local_port: {getattr(self.app, 'my_udp_port', 'unknown')}",
                f"p2p_status: {self.status}",
            ]
        else:
            lines = ["No match info."]

        for i, line in enumerate(lines):
            txt = self.small_font.render(line, True, GRAY)
            surface.blit(txt, (WIDTH//2 - 300, 200 + i * 30))