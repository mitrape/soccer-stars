# client/main.py
import os
import sys
import pygame

# Allow imports like "from shared.constants import ..."
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared.constants import APP_TITLE, WIDTH, HEIGHT, FPS, BLACK, WHITE
from client.screens import SplashScreen, LoginScreen, LobbyScreen, GameScreen

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(APP_TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont(None, 22)

        # Screen registry
        self.screens = {
            "splash": SplashScreen(self),
            "login": LoginScreen(self),
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
        # Global shortcuts: 1/2/3/4 from anywhere
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.change_screen("splash")
            elif event.key == pygame.K_2:
                self.change_screen("login")
            elif event.key == pygame.K_3:
                self.change_screen("lobby")
            elif event.key == pygame.K_4:
                self.change_screen("game")
            elif event.key == pygame.K_ESCAPE:
                self.running = False

    def draw_footer(self):
        text = "ESC: Quit | 1 Splash | 2 Login | 3 Lobby | 4 Game"
        img = self.font.render(text, True, WHITE)
        rect = img.get_rect(midbottom=(WIDTH//2, HEIGHT - 8))
        # small shadow
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
