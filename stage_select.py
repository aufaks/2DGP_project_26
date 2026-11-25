import os

from pico2d import (
    SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDL_MOUSEMOTION, SDLK_DOWN,
    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_UP, SDLK_LEFT,
    SDLK_RIGHT, load_image,
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
        self.ui = [load_image(os.path.join('sprite', f'select_ui_{i}.png'))
                   for i in range(4)]
        self.dim = load_image(os.path.join('sprite', 'select_dim.png'))
        label_dir = os.path.join('sprite', 'select_labels')
        self.labels = {os.path.splitext(name)[0]: load_image(os.path.join(label_dir, name))
                       for name in os.listdir(label_dir) if name.endswith('.png')}
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
        if self.mode == 'world':
            self._draw_worlds()
        else:
            self._draw_stages()

    def _draw_worlds(self):
        self.images[self.world - 1].draw(640, 360, 1280, 720)
        self.dim.opacify(.64)
        self.dim.draw(640, 360, 1280, 720)
        self._label('world_select', 160, 639, 34)
        self._label('choose', 210, 591, 20)
        for index, center in enumerate(self.CARD_X):
            world = index + 1
            selected = world == self.world
            self.ui[0].opacify(1.0 if selected else .64)
            self.ui[0].draw(center, 354, 290, 300)
            self.images[index].opacify(1.0 if selected else .72)
            self.images[index].draw(center, 370, 174, 98)
            self.images[index].opacify(1.0)
            self._label(f'world_{world}', center, 300, 18)
            self._label(f'name_{world}', center, 271, 20, 180)
        self.ui[0].opacify(1.0)
        self._label('guide', 235, 66, 16)

    def _draw_stages(self):
        self.images[self.world - 1].draw(640, 360, 1280, 720)
        self.ui[2].draw(214, 360, 450, 720)
        self._label(f'world_heading_{self.world}', 214, 625, 16)
        self._label(f'name_{self.world}', 214, 585, 28, 270)
        self._label('stage_select', 214, 548, 17)
        for stage in range(1, STAGES_PER_WORLD + 1):
            left = self.STAGE_LEFT + ((stage - 1) % 3) * self.STAGE_STEP_X
            bottom = self.STAGE_TOP - ((stage - 1) // 3) * self.STAGE_STEP_Y
            available = self.available(stage)
            selected = stage == self.stage
            self.ui[1].opacify(1.0 if selected else .60 if available else .38)
            self.ui[1].draw(left + 46, bottom + 46, 104, 104)
            self._label(f'stage_{self.world}_{stage}', left + 46, bottom + 52, 21)
            self._label('play' if available else 'soon', left + 46, bottom + 29, 11)
        self.ui[1].opacify(1.0)
        self.ui[3].draw(118, 51, 185, 72)
        self._label('back', 118, 49, 15, 120)

    def _label(self, key, x, y, height, max_width=None):
        image = self.labels[key]
        width = height * image.w / image.h
        if max_width is not None and width > max_width:
            height *= max_width / width
            width = max_width
        image.draw(x, y, width, height)
