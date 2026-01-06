import os
import sys
import pygame

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared.constants import APP_TITLE, WIDTH, HEIGHT, FPS, BLACK, WHITE
from client.screens import SplashScreen, LoginScreen, SignupScreen, LobbyScreen, GameScreen
from client.network import TcpClient



class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(APP_TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 22)

        # ---- server settings ----
        self.server_host = "127.0.0.1"
        self.server_port = 9000

        # choose a UDP port for each client (IMPORTANT: if you run 2 clients on 1 PC, use different ports)
        self.my_udp_port = 10001

        # ---- session state ----
        self.me = None
        self.match_info = None

        # ---- networking ----
        self.net = TcpClient()

        self.screens = {
            "splash": SplashScreen(self),
            "login": LoginScreen(self),
            "signup": SignupScreen(self),
            "lobby": LobbyScreen(self),
            "game": GameScreen(self),
        }

        self.current = None
        self.change_screen("splash")

        self.running = True

    def change_screen(self, name, **kwargs):
        if self.current:
            self.current.on_exit()
        self.current = self.screens[name]
        self.current.on_enter(**kwargs)

    def handle_global_keys(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False

    def draw_footer(self):
        text = "ESC: Quit"
        img = self.font.render(text, True, WHITE)
        rect = img.get_rect(midbottom=(WIDTH//2, HEIGHT - 8))
        shadow = self.font.render(text, True, BLACK)
        self.screen.blit(shadow, (rect.x + 1, rect.y + 1))
        self.screen.blit(img, rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.handle_global_keys(event)
                self.current.handle_event(event)

            self.current.update(dt)
            self.current.draw(self.screen)
            self.draw_footer()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    App().run()
