import os
import time

from pico2d import *


class MainCharacter:
    MOVE_SPEED = 240.0
    JUMP_SPEED = 650.0
    GRAVITY = 1800.0
    MAX_DELTA_TIME = 0.1

    FRAME_WIDTH = 155
    FRAME_HEIGHT = 132
    FRAME_LEFT = 178
    FRAME_ROWS = {
        'IDLE': (0, 6, 8.0),
        'RUN': (136, 8, 12.0),
        'JUMP': (266, 3, 10.0),
        'FALL': (400, 2, 8.0),
        'LAND': (532, 3, 12.0),
    }

    COLLIDER_WIDTH = 36.0
    COLLIDER_HEIGHT = 60.0

    def __init__(self, x=400.0, y=50.0, ground_y=50.0):
        sprite_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'sprite',
            'MC_common_move.png',
        )
        self.image = load_image(sprite_path)

        self.x = float(x)
        self.y = float(y)
        self.ground_y = float(ground_y)
        self.velocity_y = 0.0
        self.grounded = self.y <= self.ground_y
        if self.grounded:
            self.y = self.ground_y

        self.facing_left = False
        self.pressed_keys = set()
        self.state = 'IDLE' if self.grounded else 'FALL'
        self.animation_time = 0.0
        self.last_update_time = time.perf_counter()

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
            if event.key == SDLK_SPACE and self.grounded:
                self.grounded = False
                self.velocity_y = self.JUMP_SPEED
                self._set_state('JUMP')
        elif event.type == SDL_KEYUP:
            self.pressed_keys.discard(event.key)

    def update(self, dt=None):
        now = time.perf_counter()
        if dt is None:
            dt = now - self.last_update_time
        self.last_update_time = now
        dt = max(0.0, min(float(dt), self.MAX_DELTA_TIME))

        move_x = int(
            SDLK_RIGHT in self.pressed_keys or SDLK_d in self.pressed_keys
        ) - int(
            SDLK_LEFT in self.pressed_keys or SDLK_a in self.pressed_keys
        )
        self.x += move_x * self.MOVE_SPEED * dt
        if move_x:
            self.facing_left = move_x < 0

        was_grounded = self.grounded
        if not self.grounded:
            self.velocity_y -= self.GRAVITY * dt
            self.y += self.velocity_y * dt
            if self.y <= self.ground_y:
                self.y = self.ground_y
                self.velocity_y = 0.0
                self.grounded = True

        if not self.grounded:
            self._set_state('JUMP' if self.velocity_y > 0 else 'FALL')
        elif not was_grounded:
            self._set_state('LAND')
        elif self.state == 'LAND':
            _, frame_count, frames_per_second = self.FRAME_ROWS['LAND']
            if self.animation_time >= frame_count / frames_per_second:
                self._set_state('RUN' if move_x else 'IDLE')
        else:
            self._set_state('RUN' if move_x else 'IDLE')

        self.animation_time += dt

    def draw(self):
        row_top, frame_count, frames_per_second = self.FRAME_ROWS[self.state]
        frame_index = int(self.animation_time * frames_per_second)
        if self.state in ('IDLE', 'RUN', 'FALL'):
            frame_index %= frame_count
        else:
            frame_index = min(frame_index, frame_count - 1)

        source_x = self.FRAME_LEFT + frame_index * self.FRAME_WIDTH
        source_y = self.image.h - row_top - self.FRAME_HEIGHT
        self.image.clip_composite_draw(
            source_x,
            source_y,
            self.FRAME_WIDTH,
            self.FRAME_HEIGHT,
            0,
            'h' if self.facing_left else '',
            self.x,
            self.y + self.FRAME_HEIGHT / 2,
            self.FRAME_WIDTH,
            self.FRAME_HEIGHT,
        )

    def get_collision_box(self):
        return (
            self.x - self.COLLIDER_WIDTH / 2,
            self.y,
            self.x + self.COLLIDER_WIDTH / 2,
            self.y + self.COLLIDER_HEIGHT,
        )

    def _set_state(self, state):
        if self.state != state:
            self.state = state
            self.animation_time = 0.0
