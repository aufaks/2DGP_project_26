import os

from pico2d import (
    SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDL_MOUSEMOTION, SDLK_DOWN,
    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_UP, draw_rectangle,
    load_font, load_image,
)


class TitleScreen:
    WIDTH = 1280
    HEIGHT = 720
    BUTTON_LEFT = 1000
    BUTTON_RIGHT = 1212
    BUTTON_HEIGHT = 52
    BUTTON_BOTTOMS = (154, 88)
    LABELS = ('게임 시작', '종료')

    def __init__(self):
        self.background = load_image(os.path.join('sprite', 'title_screen.png'))
        fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
        font_path = os.path.join(fonts_dir, 'malgun.ttf')
        if not os.path.isfile(font_path):
            font_path = os.path.join(fonts_dir, 'arial.ttf')
            self.labels = ('START', 'QUIT')
        else:
            self.labels = self.LABELS
        self.font = load_font(font_path, 25)
        self.selected = 0

    def button_at(self, x, y):
        # SDL mouse coordinates start at the top; pico2d drawing starts at the bottom.
        y = self.HEIGHT - y
        for index, bottom in enumerate(self.BUTTON_BOTTOMS):
            if (self.BUTTON_LEFT <= x <= self.BUTTON_RIGHT
                    and bottom <= y <= bottom + self.BUTTON_HEIGHT):
                return index
        return None

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                return 'quit'
            if event.key in (SDLK_UP, SDLK_DOWN):
                self.selected = 1 - self.selected
            elif event.key in (SDLK_RETURN, SDLK_SPACE):
                return ('start', 'quit')[self.selected]
        elif event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN):
            index = self.button_at(event.x, event.y)
            if index is not None:
                self.selected = index
                if event.type == SDL_MOUSEBUTTONDOWN and event.button == 1:
                    return ('start', 'quit')[index]
        return None

    def draw(self):
        self.background.draw(self.WIDTH // 2, self.HEIGHT // 2,
                             self.WIDTH, self.HEIGHT)
        for index, bottom in enumerate(self.BUTTON_BOTTOMS):
            selected = index == self.selected
            fill = (21, 40, 88) if selected else (46, 68, 113)
            draw_rectangle(self.BUTTON_LEFT, bottom, self.BUTTON_RIGHT,
                           bottom + self.BUTTON_HEIGHT, *fill, filled=True)
            if selected:
                draw_rectangle(self.BUTTON_LEFT, bottom, self.BUTTON_LEFT + 5,
                               bottom + self.BUTTON_HEIGHT, 84, 232, 242,
                               filled=True)
            self.font.draw(self.BUTTON_LEFT + 27, bottom + 15,
                           self.labels[index], (246, 248, 255))
