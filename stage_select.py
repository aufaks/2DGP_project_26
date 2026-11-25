import os

from pico2d import pico2d as pico2d_core
from sdl2 import SDL_BLENDMODE_BLEND, SDL_SetRenderDrawBlendMode
from pico2d import (
    SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDL_MOUSEMOTION, SDLK_DOWN,
    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_UP, SDLK_LEFT,
    SDLK_RIGHT, draw_rectangle, load_font, load_image,
)

from stage_progress import STAGES_PER_WORLD, WORLD_COUNT, stage_path


class StageSelect:
    WIDTH = 1280
    HEIGHT = 720
    WORLD_NAMES = ('구름 위의 길', '유적 외곽', '유적 내부', '메아리의 중심')
    CARD_X = (176, 484, 792, 1100)
    CARD_Y = 340
    STAGE_LEFT = 56
    STAGE_TOP = 430
    STAGE_STEP_X = 114
    STAGE_STEP_Y = 106
    STAGE_SIZE = 92

    def __init__(self):
        self.images = [load_image(os.path.join('sprite',
                       f'world_{world:02d}_select.png'))
                       for world in range(1, WORLD_COUNT + 1)]
        fonts = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
        korean = os.path.join(fonts, 'malgun.ttf')
        font_path = korean if os.path.isfile(korean) else os.path.join(fonts, 'arial.ttf')
        self.korean = os.path.isfile(korean)
        self.heading = load_font(font_path, 40)
        self.body = load_font(font_path, 22)
        self.small = load_font(font_path, 16)
        self.mode = 'world'
        self.world = 1
        self.stage = 1

    def show_worlds(self):
        self.mode = 'world'

    def show_stages(self, world):
        self.world = world
        self.stage = 1
        self.mode = 'stages'

    def available(self, stage):
        return stage_path(self.world, stage).is_file()

    def hit_test(self, x, y):
        y = self.HEIGHT - y
        if self.mode == 'world':
            for index, center in enumerate(self.CARD_X):
                if center - 142 <= x <= center + 142 and 222 <= y <= 486:
                    return index + 1
            return None
        if 35 <= x <= 202 and 30 <= y <= 72:
            return 'back'
        for stage in range(1, STAGES_PER_WORLD + 1):
            left = self.STAGE_LEFT + ((stage - 1) % 3) * self.STAGE_STEP_X
            bottom = self.STAGE_TOP - ((stage - 1) // 3) * self.STAGE_STEP_Y
            if left <= x <= left + self.STAGE_SIZE and bottom <= y <= bottom + self.STAGE_SIZE:
                return stage
        return None

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                if self.mode == 'stages':
                    self.show_worlds()
                else:
                    return ('title',)
            elif self.mode == 'world':
                if event.key == SDLK_LEFT:
                    self.world = max(1, self.world - 1)
                elif event.key == SDLK_RIGHT:
                    self.world = min(WORLD_COUNT, self.world + 1)
                elif event.key in (SDLK_RETURN, SDLK_SPACE):
                    self.show_stages(self.world)
            else:
                if event.key == SDLK_LEFT:
                    self.stage = max(1, self.stage - 1)
                elif event.key == SDLK_RIGHT:
                    self.stage = min(STAGES_PER_WORLD, self.stage + 1)
                elif event.key == SDLK_UP:
                    self.stage = max(1, self.stage - 3)
                elif event.key == SDLK_DOWN:
                    self.stage = min(STAGES_PER_WORLD, self.stage + 3)
                elif event.key in (SDLK_RETURN, SDLK_SPACE) and self.available(self.stage):
                    return ('play', self.world, self.stage)
        elif event.type in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN):
            hit = self.hit_test(event.x, event.y)
            if self.mode == 'world' and isinstance(hit, int):
                self.world = hit
                if event.type == SDL_MOUSEBUTTONDOWN and event.button == 1:
                    self.show_stages(hit)
            elif self.mode == 'stages':
                if isinstance(hit, int):
                    self.stage = hit
                if event.type == SDL_MOUSEBUTTONDOWN and event.button == 1:
                    if hit == 'back':
                        self.show_worlds()
                    elif isinstance(hit, int) and self.available(hit):
                        return ('play', self.world, hit)
        return None

    def draw(self):
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
        if self.mode == 'world':
            self._draw_worlds()
        else:
            self._draw_stages()

    def _draw_worlds(self):
        self.images[self.world - 1].draw(640, 360, 1280, 720)
        draw_rectangle(0, 0, 1280, 720, 15, 27, 58, 205, filled=True)
        self.heading.draw(64, 618, '월드 선택' if self.korean else 'SELECT WORLD', (247, 248, 255))
        self.body.draw(68, 574, '탐험할 장소를 선택하세요' if self.korean else 'Choose a world', (183, 218, 240))
        for index, center in enumerate(self.CARD_X):
            world = index + 1
            selected = world == self.world
            left, right = center - 142, center + 142
            draw_rectangle(left - 3, 219, right + 3, 490,
                           *( (99, 232, 245) if selected else (95, 115, 165) ), filled=True)
            draw_rectangle(left, 222, right, 487, 24, 39, 81, filled=True)
            self.images[index].draw(center, 390, 278, 157)
            self.body.draw(left + 14, 273, f'WORLD {world:02d}', (110, 237, 241))
            name = self.WORLD_NAMES[index] if self.korean else ('SKY PATH', 'OUTSKIRTS', 'INNER RUINS', 'ECHO CORE')[index]
            self.body.draw(left + 14, 238, name, (246, 248, 255))
        self.small.draw(66, 64, '← → 선택   ·   ENTER 확인   ·   ESC 돌아가기' if self.korean
                        else 'LEFT / RIGHT  ·  ENTER TO SELECT  ·  ESC TO RETURN', (213, 225, 244))

    def _draw_stages(self):
        self.images[self.world - 1].draw(640, 360, 1280, 720)
        draw_rectangle(0, 0, 428, 720, 17, 32, 70, 240, filled=True)
        self.small.draw(38, 652, f'WORLD {self.world:02d} / 04', (112, 228, 241))
        name = self.WORLD_NAMES[self.world - 1] if self.korean else ('SKY PATH', 'OUTSKIRTS', 'INNER RUINS', 'ECHO CORE')[self.world - 1]
        self.heading.draw(36, 597, name, (246, 248, 255))
        self.small.draw(38, 558, '스테이지 선택' if self.korean else 'SELECT STAGE', (183, 218, 240))
        for stage in range(1, STAGES_PER_WORLD + 1):
            left = self.STAGE_LEFT + ((stage - 1) % 3) * self.STAGE_STEP_X
            bottom = self.STAGE_TOP - ((stage - 1) // 3) * self.STAGE_STEP_Y
            available = self.available(stage)
            selected = stage == self.stage
            if selected:
                draw_rectangle(left - 3, bottom - 3, left + self.STAGE_SIZE + 3,
                               bottom + self.STAGE_SIZE + 3, 101, 232, 245, filled=True)
            draw_rectangle(left, bottom, left + self.STAGE_SIZE,
                           bottom + self.STAGE_SIZE,
                           *((39, 77, 115) if available else (33, 49, 78)), filled=True)
            self.body.draw(left + 16, bottom + 42, f'{self.world}-{stage}',
                           (248, 249, 255) if available else (143, 157, 182))
            self.small.draw(left + 12, bottom + 14,
                            ('입장' if available else '준비 중') if self.korean
                            else ('PLAY' if available else 'SOON'),
                            (112, 231, 239) if available else (132, 146, 171))
        draw_rectangle(35, 30, 202, 72, 49, 76, 119, filled=True)
        self.small.draw(52, 42, '← 월드 선택' if self.korean else '< WORLDS', (248, 249, 255))
