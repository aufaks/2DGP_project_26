import os

from pico2d import (
    SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDL_MOUSEMOTION, SDLK_DOWN,
    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_UP,
    load_image,
)


class PauseMenu:
    WIDTH = 1280
    HEIGHT = 720
    PANEL_LEFT = 390
    PANEL_BOTTOM = 180
    PANEL_RIGHT = 890
    PANEL_TOP = 540
    BUTTON_LEFT = 460
    BUTTON_RIGHT = 820
    BUTTON_HEIGHT = 56
    BUTTON_BOTTOMS = (380, 300, 220)
    ACTIONS = ('continue', 'restart', 'title')

    def __init__(self):
        self.dim = load_image(os.path.join('sprite', 'pause_dim.png'))
        self.panel = load_image(os.path.join('sprite', 'pause_art_0.png'))
        self.heading = load_image(os.path.join('sprite', 'pause_heading.png'))
        self.buttons = [load_image(os.path.join('sprite', f'pause_art_{i}.png'))
                        for i in range(1, 4)]
        self.selected = 0

    def button_at(self, x, y):
        y = self.HEIGHT - y
        for index, bottom in enumerate(self.BUTTON_BOTTOMS):
            if (self.BUTTON_LEFT <= x <= self.BUTTON_RIGHT
                    and bottom <= y <= bottom + self.BUTTON_HEIGHT):
                return index
        return None

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                return 'continue'
            if event.key in (SDLK_UP, SDLK_DOWN):
                direction = -1 if event.key == SDLK_UP else 1
                self.selected = (self.selected + direction) % len(self.ACTIONS)
            elif event.key in (SDLK_RETURN, SDLK_SPACE):
                return self.ACTIONS[self.selected]
        elif event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN):
            index = self.button_at(event.x, event.y)
            if index is not None:
                self.selected = index
                if event.type == SDL_MOUSEBUTTONDOWN and event.button == 1:
                    return self.ACTIONS[index]
        return None

    def draw(self):
        self.dim.opacify(0.72)
        self.dim.draw(self.WIDTH / 2, self.HEIGHT / 2, self.WIDTH, self.HEIGHT)
        self.panel.draw(640, 365, 560, 540)
        self.heading.draw(640, 478, 240, 70)
        for index, bottom in enumerate(self.BUTTON_BOTTOMS):
            selected = index == self.selected
            button = self.buttons[index]
            button.opacify(1.0 if selected else 0.62)
            button.draw((self.BUTTON_LEFT + self.BUTTON_RIGHT) / 2,
                        bottom + self.BUTTON_HEIGHT / 2, 380, 100)
            button.opacify(1.0)
