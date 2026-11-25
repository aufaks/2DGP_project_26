import os

from sdl2 import SDL_BLENDMODE_BLEND, SDL_SetRenderDrawBlendMode
from pico2d import (
    SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDL_MOUSEMOTION, SDLK_DOWN,
    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_UP,
    draw_rectangle, load_font,
)
from pico2d import pico2d as pico2d_core


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
        fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
        korean_font = os.path.join(fonts_dir, 'malgun.ttf')
        if os.path.isfile(korean_font):
            font_path = korean_font
            self.heading_label = '일시정지'
            self.labels = ('계속', '스테이지 재시작', '타이틀 화면')
        else:
            font_path = os.path.join(fonts_dir, 'arial.ttf')
            self.heading_label = 'PAUSED'
            self.labels = ('CONTINUE', 'RESTART STAGE', 'TITLE SCREEN')
        self.heading = load_font(font_path, 38)
        self.font = load_font(font_path, 25)
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
                self.selected = (self.selected + 1) % len(self.ACTIONS)
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
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
        draw_rectangle(0, 0, self.WIDTH, self.HEIGHT, 5, 10, 23, 190,
                       filled=True)
        draw_rectangle(self.PANEL_LEFT, self.PANEL_BOTTOM,
                       self.PANEL_RIGHT, self.PANEL_TOP,
                       20, 34, 62, 245, filled=True)
        self.heading.draw(570, 475, self.heading_label, (246, 248, 255))

        for index, bottom in enumerate(self.BUTTON_BOTTOMS):
            selected = index == self.selected
            fill = (21, 40, 88) if selected else (46, 68, 113)
            draw_rectangle(self.BUTTON_LEFT, bottom, self.BUTTON_RIGHT,
                           bottom + self.BUTTON_HEIGHT, *fill, filled=True)
            if selected:
                draw_rectangle(self.BUTTON_LEFT, bottom,
                               self.BUTTON_LEFT + 5,
                               bottom + self.BUTTON_HEIGHT,
                               84, 232, 242, filled=True)
            self.font.draw(self.BUTTON_LEFT + 24, bottom + 16,
                           self.labels[index], (246, 248, 255))
