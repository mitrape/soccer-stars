# client/ui.py
import pygame

class Label:
    def __init__(self, text, pos, font, color):
        self.text = text
        self.pos = pos
        self.font = font
        self.color = color

    def draw(self, surface):
        img = self.font.render(self.text, True, self.color)
        surface.blit(img, self.pos)


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
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)
