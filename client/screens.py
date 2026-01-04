# client/screens.py
import pygame
from shared.constants import WIDTH, HEIGHT, WHITE, BLACK, GRAY, DARK, BLUE, GREEN, ORANGE
from client.ui import Button

class Screen:
    """Base class for all screens."""
    name = "base"

    def __init__(self, app):
        self.app = app

    def on_enter(self, **kwargs):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class SplashScreen(Screen):
    name = "splash"

    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 64)
        self.small_font = pygame.font.SysFont(None, 26)
        self.go_btn = Button((WIDTH//2 - 140, HEIGHT//2 + 80, 280, 55), "Go to Login (2)", self.small_font, BLUE, WHITE)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_2:
                self.app.change_screen("login")
        if self.go_btn.is_clicked(event):
            self.app.change_screen("login")

    def draw(self, surface):
        surface.fill(DARK)
        title = self.title_font.render("SOCCER STARS", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))

        tip = self.small_font.render("Press 1/2/3/4 to switch screens (Phase 0)", True, GRAY)
        surface.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT//2 + 20)))

        self.go_btn.draw(surface)


class LoginScreen(Screen):
    name = "login"

    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 26)
        self.lobby_btn = Button((WIDTH//2 - 140, HEIGHT//2 + 80, 280, 55), "Go to Lobby (3)", self.small_font, GREEN, WHITE)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_3:
                self.app.change_screen("lobby")
        if self.lobby_btn.is_clicked(event):
            self.app.change_screen("lobby")

    def draw(self, surface):
        surface.fill((18, 24, 36))
        title = self.title_font.render("Login / Register (Stub)", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))

        msg = self.small_font.render("Next phase: connect to TCP server + input fields.", True, GRAY)
        surface.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 10)))

        self.lobby_btn.draw(surface)


class LobbyScreen(Screen):
    name = "lobby"

    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 26)
        self.game_btn = Button((WIDTH//2 - 140, HEIGHT//2 + 80, 280, 55), "Go to Game (4)", self.small_font, ORANGE, BLACK)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_4:
                self.app.change_screen("game")
        if self.game_btn.is_clicked(event):
            self.app.change_screen("game")

    def draw(self, surface):
        surface.fill((24, 40, 28))
        title = self.title_font.render("Lobby (Stub)", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))

        msg = self.small_font.render("Next phase: show online users + invite flow.", True, GRAY)
        surface.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 10)))

        self.game_btn.draw(surface)


class GameScreen(Screen):
    name = "game"

    def __init__(self, app):
        super().__init__(app)
        self.title_font = pygame.font.SysFont(None, 54)
        self.small_font = pygame.font.SysFont(None, 26)
        self.back_btn = Button((20, 20, 180, 45), "Back to Splash (1)", self.small_font, BLUE, WHITE)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.app.change_screen("splash")
        if self.back_btn.is_clicked(event):
            self.app.change_screen("splash")

    def draw(self, surface):
        surface.fill((40, 24, 24))
        title = self.title_font.render("Game Screen (Stub)", True, WHITE)
        surface.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))

        msg = self.small_font.render("Next phase: draw field + pieces + aiming.", True, GRAY)
        surface.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 10)))

        self.back_btn.draw(surface)
