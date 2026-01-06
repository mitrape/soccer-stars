import pygame

class Button:
    def __init__(self, rect, text, font, bg, fg):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=10)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, width=2, border_radius=10)
        txt = self.font.render(self.text, True, self.fg)
        surface.blit(txt, txt.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


class TextInput:
    def __init__(self, rect, font, placeholder="", is_password=False):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.placeholder = placeholder
        self.is_password = is_password
        self.text = ""
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                pass
            else:
                # keep it simple (printable chars)
                if event.unicode and event.unicode.isprintable():
                    self.text += event.unicode

    def draw(self, surface):
        bg = (240, 240, 240) if self.active else (220, 220, 220)
        pygame.draw.rect(surface, bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, width=2, border_radius=8)

        shown = self.text
        if self.is_password and shown:
            shown = "*" * len(shown)

        if not shown:
            img = self.font.render(self.placeholder, True, (120, 120, 120))
        else:
            img = self.font.render(shown, True, (20, 20, 20))

        surface.blit(img, (self.rect.x + 10, self.rect.y + 10))

    def value(self):
        return self.text.strip()
