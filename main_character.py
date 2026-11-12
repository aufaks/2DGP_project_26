import os

from pico2d import *


class MainCharacter:
    DRAW_SIZE = 96.0
    PIXELS_PER_METER = DRAW_SIZE / 1.2
    RUN_SPEED_KMPH = 10.0
    RUN_SPEED_MPS = RUN_SPEED_KMPH * 1000.0 / 3600.0
    MOVE_SPEED = RUN_SPEED_MPS * PIXELS_PER_METER
    JUMP_SPEED = 900.0
    GRAVITY = 1500.0
    MAX_DELTA_TIME = 0.1

    FRAME_WIDTH = 254
    FRAME_HEIGHT = 254
    FRAME_COUNT = 8
    RUN_FIRST_FRAME = 1
    STRIDE_LENGTH_M = 0.8
    RUN_FRAMES_PER_STRIDE = FRAME_COUNT - RUN_FIRST_FRAME
    RUN_FRAMES_PER_SECOND = (
        RUN_SPEED_MPS / STRIDE_LENGTH_M * RUN_FRAMES_PER_STRIDE
    )
    RUN_FRAME_DURATION = 1.0 / RUN_FRAMES_PER_SECOND
    IDLE_FRAME_COUNT = 6
    FRAMES_PER_SECOND = 8.0
    FRAME_DURATION = 1.0 / FRAMES_PER_SECOND
    AIR_FRAME_COUNT = 10
    JUMP_FRAME_COUNT = 4
    JUMP_FIRST_FRAME = 1
    FALL_FRAME_COUNT = 3
    LAND_FRAME_COUNT = 3
    FRAME_FOOT_OFFSET = 24
    LAND_DURATION = LAND_FRAME_COUNT * FRAME_DURATION

    COLLIDER_WIDTH = 36.0
    COLLIDER_HEIGHT = 60.0

    def __init__(self, x=400.0, y=50.0, ground_y=50.0, collision_map=None):
        sprite_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'sprite',
        )
        self.run_image = load_image(os.path.join(sprite_dir, 'mc_run.png'))
        self.idle_image = load_image(os.path.join(sprite_dir, 'mc_idle.png'))
        self.air_image = load_image(
            os.path.join(sprite_dir, 'mc_jump_fall_land.png')
        )

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
        if not self.is_moving:
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
            self._set_state('RUN' if move_x else 'LAND')
        elif self.state == 'LAND':
            if move_x:
                self._set_state('RUN')
            elif self.animation_time >= self.LAND_DURATION:
                self._set_state('IDLE')
        else:
            self._set_state('RUN' if move_x else 'IDLE')

        self.animation_time += dt
        if self.state == 'RUN' and self.is_moving:
            self.run_animation_time += dt

    def draw(self, camera=None):
        if self.state == 'JUMP':
            frame_index = self.JUMP_FIRST_FRAME + min(
                int(self.animation_time / self.FRAME_DURATION),
                self.JUMP_FRAME_COUNT - self.JUMP_FIRST_FRAME - 1,
            )
            image = self.air_image
        elif self.state == 'FALL':
            frame_index = self.JUMP_FRAME_COUNT + (
                int(self.animation_time / self.FRAME_DURATION)
                % self.FALL_FRAME_COUNT
            )
            image = self.air_image
        elif self.state == 'LAND':
            frame_index = self.JUMP_FRAME_COUNT + self.FALL_FRAME_COUNT + min(
                int(self.animation_time / self.FRAME_DURATION),
                self.LAND_FRAME_COUNT - 1,
            )
            image = self.air_image
        elif self.state == 'IDLE':
            frame_index = (
                int(self.animation_time / self.FRAME_DURATION)
                % self.IDLE_FRAME_COUNT
            )
            image = self.idle_image
        else:
            frame_index = (
                self.RUN_FIRST_FRAME
                + int(self.run_animation_time / self.RUN_FRAME_DURATION)
                % (self.FRAME_COUNT - self.RUN_FIRST_FRAME)
                if self.is_moving
                else 0
            )
            image = self.run_image

        source_x = frame_index * self.FRAME_WIDTH
        draw_size = self.DRAW_SIZE
        draw_x = self.x
        draw_y = self.y + draw_size / 2 - (
            self.FRAME_FOOT_OFFSET * draw_size / self.FRAME_HEIGHT
        )
        if camera is not None:
            draw_x, draw_y = camera.world_to_screen(draw_x, draw_y)
            draw_size = camera.transform_size(draw_size)
        image.clip_composite_draw(
            source_x,
            0,
            self.FRAME_WIDTH,
            self.FRAME_HEIGHT,
            0,
            'h' if self.facing_left else '',
            draw_x,
            draw_y,
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
            if state == 'RUN':
                self.run_animation_time = 0.0
