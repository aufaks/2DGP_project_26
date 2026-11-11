import os

from pico2d import *


class MainCharacter:
    MOVE_SPEED = 240.0
    JUMP_SPEED = 650.0
    GRAVITY = 1800.0
    MAX_DELTA_TIME = 0.1

    FRAME_WIDTH = 254
    FRAME_HEIGHT = 254
    FRAME_COUNT = 8
    FRAMES_PER_SECOND = 8.0
    DRAW_SIZE = 96.0
    FRAME_FOOT_OFFSET = 24
    LAND_DURATION = 0.25

    COLLIDER_WIDTH = 36.0
    COLLIDER_HEIGHT = 60.0

    def __init__(self, x=400.0, y=50.0, ground_y=50.0, collision_map=None):
        sprite_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'sprite',
            'mc_run.png',
        )
        self.image = load_image(sprite_path)

        self.x = float(x)
        self.y = float(y)
        self.ground_y = float(ground_y)
        self.collision_map = collision_map
        self.velocity_y = 0.0
        self.grounded = (
            collision_map.is_supported(
                self.x,
                self.y,
                self.COLLIDER_WIDTH,
            )
            if collision_map is not None
            else self.y <= self.ground_y
        )
        if self.grounded and collision_map is None:
            self.y = self.ground_y

        self.facing_left = False
        self.pressed_keys = set()
        self.is_moving = False
        self.run_animation_time = 0.0
        self.state = 'IDLE' if self.grounded else 'FALL'
        self.animation_time = 0.0

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            self.pressed_keys.add(event.key)
            if event.key == SDLK_SPACE and self.grounded:
                self.grounded = False
                self.velocity_y = self.JUMP_SPEED
                self._set_state('JUMP')
        elif event.type == SDL_KEYUP:
            self.pressed_keys.discard(event.key)

    def update(self, dt=1 / 60):
        dt = max(0.0, min(float(dt), self.MAX_DELTA_TIME))

        move_x = int(
            SDLK_RIGHT in self.pressed_keys or SDLK_d in self.pressed_keys
        ) - int(
            SDLK_LEFT in self.pressed_keys or SDLK_a in self.pressed_keys
        )
        self.is_moving = bool(move_x)
        if self.is_moving:
            self.run_animation_time += dt
        else:
            self.run_animation_time = 0.0

        was_grounded = self.grounded
        if self.collision_map is None:
            self.x += move_x * self.MOVE_SPEED * dt
        if move_x:
            self.facing_left = move_x < 0

        movement_y = 0.0
        if not self.grounded:
            self.velocity_y -= self.GRAVITY * dt
            movement_y = self.velocity_y * dt

        if self.collision_map is not None:
            self.x, self.y, self.grounded, hit_ceiling = \
                self.collision_map.move_actor(
                    self.x,
                    self.y,
                    self.COLLIDER_WIDTH,
                    self.COLLIDER_HEIGHT,
                    move_x * self.MOVE_SPEED * dt,
                    movement_y,
                )
            if self.grounded or hit_ceiling:
                self.velocity_y = 0.0
        elif not self.grounded:
            self.y += movement_y
            if self.y <= self.ground_y:
                self.y = self.ground_y
                self.velocity_y = 0.0
                self.grounded = True

        if not self.grounded:
            self._set_state('JUMP' if self.velocity_y > 0 else 'FALL')
        elif not was_grounded:
            self._set_state('LAND')
        elif self.state == 'LAND':
            if self.animation_time >= self.LAND_DURATION:
                self._set_state('RUN' if move_x else 'IDLE')
        else:
            self._set_state('RUN' if move_x else 'IDLE')

        self.animation_time += dt

    def draw(self):
        frame_index = (
            int(self.run_animation_time * self.FRAMES_PER_SECOND)
            % self.FRAME_COUNT
            if self.is_moving
            else 0
        )
        source_x = frame_index * self.FRAME_WIDTH
        draw_size = self.DRAW_SIZE
        foot_offset = (
            self.FRAME_FOOT_OFFSET * draw_size / self.FRAME_HEIGHT
        )
        self.image.clip_composite_draw(
            source_x,
            0,
            self.FRAME_WIDTH,
            self.FRAME_HEIGHT,
            0,
            'h' if self.facing_left else '',
            self.x,
            self.y + draw_size / 2 - foot_offset,
            draw_size,
            draw_size,
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
