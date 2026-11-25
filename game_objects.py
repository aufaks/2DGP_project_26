import math

from pico2d import draw_circle, draw_line, draw_rectangle
from pico2d import pico2d as pico2d_core
from sdl2 import SDL_BLENDMODE_BLEND, SDL_SetRenderDrawBlendMode


def _screen_rect(rect, camera):
    left, bottom, right, top = rect
    if camera is None:
        return left, bottom, right, top

    left, bottom = camera.world_to_screen(left, bottom)
    right, top = camera.world_to_screen(right, top)
    return round(left), round(bottom), round(right), round(top)


def _draw_sprite(image, rect, camera, width, height, bottom_offset=0):
    left, bottom, right, _ = rect
    center_x = (left + right) / 2
    center_y = bottom + bottom_offset + height / 2
    if camera is not None:
        center_x, center_y = camera.world_to_screen(center_x, center_y)
        width = camera.transform_size(width)
        height = camera.transform_size(height)
    image.clip_composite_draw(0, 0, image.w, image.h, 0, '',
                              center_x, center_y, width, height)


def _draw_signal_marks(left, bottom, right, size, count):
    color = (119, 226, 237) if count == 1 else (231, 173, 246)
    for index in range(count):
        x = (left + right) / 2 + (index - (count - 1) / 2) * size * 2
        draw_rectangle(x - size / 2, bottom, x + size / 2, bottom + size,
                       *color, filled=True)


class EchoDevice:
    """Non-solid pickup that unlocks echo recording and playback."""

    def __init__(self, object_id, rect, interaction_range=64.0):
        self.object_id = object_id
        self.rect = rect
        self.interaction_range = interaction_range
        self.collected = False

    def can_collect(self, actor):
        if self.collected:
            return False
        left, bottom, right, top = self.rect
        al, ab, ar, at = actor.get_collision_box()
        dx, dy = max(left - ar, al - right, 0), max(bottom - at, ab - top, 0)
        return dx * dx + dy * dy <= self.interaction_range ** 2

    def collect(self, actor):
        if not self.can_collect(actor):
            return False
        self.collected = True
        return True

    def draw(self, camera=None):
        if self.collected:
            return
        if getattr(self, 'image', None) is not None:
            _draw_sprite(self.image, self.rect, camera, 76, 96)
            return
        left, bottom, right, top = _screen_rect(self.rect, camera)
        w, h = right - left, top - bottom
        draw_rectangle(left, bottom, right, bottom + h * .22,
                       114, 119, 145, filled=True)
        draw_rectangle(left + w * .12, bottom + h * .22,
                       right - w * .12, bottom + h * .34,
                       225, 220, 202, filled=True)
        draw_rectangle(left + w * .20, bottom + h * .49,
                       right - w * .20, top, 28, 85, 112, filled=True)
        draw_rectangle(left + w * .30, bottom + h * .58,
                       right - w * .30, top - h * .09,
                       77, 229, 246, filled=True)


class StageExit:
    def __init__(self, object_id, rect, style='arch'):
        self.object_id = object_id
        self.rect = rect
        self.style = style
        self.animation_time = 0.0

    def update(self, dt):
        self.animation_time += max(0.0, dt)

    def draw(self, camera=None):
        if self.style == 'wall_glow':
            left, bottom, right, top = _screen_rect(self.rect, camera)
            SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
            pulse = (math.sin(self.animation_time * 2.4) + 1.0) * 0.5
            glow_x = right - max(7, (right - left) // 24)
            center_y = (bottom + top) / 2
            for radius, alpha in ((54, 14), (37, 22), (22, 31)):
                draw_circle(glow_x - 15, center_y, radius,
                            113, 243, 205, alpha, filled=True)
            # A broken fissure scatters light onto the wall instead of forming a doorway.
            segments = ((.10, .21, -2, 3), (.24, .36, 1, 5),
                        (.42, .49, -1, 3), (.57, .72, 2, 5),
                        (.76, .87, -1, 3), (.92, .97, 1, 2))
            for start, end, offset, width in segments:
                y1 = bottom + (top - bottom) * start
                y2 = bottom + (top - bottom) * end
                x1 = glow_x + offset
                draw_rectangle(x1 - width, y1, x1 + width, y2,
                               126, 246, 207, int(105 + 42 * pulse),
                               filled=True)
                draw_line(x1 - width, y1 + 2, x1 + width, y2 - 2,
                          237, 255, 242, int(155 + 65 * pulse))
            # Soft pools and short rays point along the ledge toward the light.
            for dx, dy, radius in ((-48, -10, 10), (-27, 6, 7), (-68, 16, 5)):
                draw_circle(glow_x + dx, center_y + dy, radius,
                            138, 248, 213, 30, filled=True)
            for offset in (-35, -13, 14, 32):
                y = center_y + offset * (top - bottom) / 105
                draw_line(glow_x - 55, y - 5, glow_x - 11, y,
                          147, 245, 210, int(32 + 24 * pulse))
            SDL_SetRenderDrawBlendMode(pico2d_core.renderer, 0)
            return
        if getattr(self, 'image', None) is not None:
            _draw_sprite(self.image, self.rect, camera, 116, 112)
            return
        left, bottom, right, top = _screen_rect(self.rect, camera)
        w, h = right - left, top - bottom
        for edge in (left, right - w * .17):
            draw_rectangle(edge, bottom, edge + w * .17, top - h * .16,
                           110, 109, 137, filled=True)
            draw_rectangle(edge + w * .06, bottom + h * .12,
                           edge + w * .11, top - h * .22, 120, 218, 223, filled=True)
        draw_rectangle(left, top - h * .22, right, top - h * .10,
                       219, 212, 196, filled=True)
        draw_rectangle(left + w * .34, top - h * .16, right - w * .34, top,
                       95, 193, 207, filled=True)


class Door:
    def __init__(self, object_id, rect, required_plates=1, latch=False, signal_marks=0):
        self.object_id = object_id
        self.rect = rect
        self.is_open = False
        self.required_plates = required_plates
        self.latch = latch
        self.pressed_count = 0
        self.signal_marks = signal_marks

    def update(self, activated, actors):
        self.pressed_count = int(activated)
        occupied = any(self._overlaps_actor(actor) for actor in actors)
        self.is_open = (self.pressed_count >= self.required_plates
                        or (self.is_open and (self.latch or occupied)))

    def _overlaps_actor(self, actor):
        left, bottom, right, top = self.rect
        actor_left, actor_bottom, actor_right, actor_top = \
            actor.get_collision_box()
        return (
            actor_right > left
            and actor_left < right
            and actor_top > bottom
            and actor_bottom < top
        )

    def draw(self, camera=None):
        if getattr(self, 'images', None) is not None:
            sprite = self.images[1 if self.is_open else 0]
            _draw_sprite(sprite, self.rect, camera, 88, 160)
            left, bottom, right, top = _screen_rect(self.rect, camera)
            _draw_signal_marks(left, top - 4, right, 3, self.signal_marks)
            if not self.is_open and self.required_plates > 1:
                spacing = (right - left) / (self.required_plates + 1)
                for index in range(self.required_plates):
                    x = left + spacing * (index + 1)
                    color = ((100, 220, 147) if index < self.pressed_count
                             else (232, 179, 84))
                    draw_rectangle(x - 2, top - 14, x + 2, top - 8,
                                   *color, filled=True)
            return
        left, bottom, right, top = _screen_rect(self.rect, camera)
        draw_rectangle(left, bottom, right, top, 57, 48, 65, filled=True)
        _draw_signal_marks(left, top - 4, right, 3, self.signal_marks)

        if self.is_open:
            draw_rectangle(
                left + 5, bottom, right - 5, top - 5,
                24, 31, 45, filled=True,
            )
            draw_rectangle(
                left + 5, bottom, right - 5, bottom + 8,
                119, 147, 161, filled=True,
            )
            return

        draw_rectangle(
            left + 5, bottom + 5, right - 5, top - 5,
            137, 82, 61, filled=True,
        )
        draw_rectangle(
            left + 10, bottom + 5, left + 13, top - 5,
            183, 122, 82, filled=True,
        )
        draw_rectangle(
            right - 15, bottom + 5, right - 12, top - 5,
            183, 122, 82, filled=True,
        )
        draw_rectangle(
            right - 13, bottom + (top - bottom) / 2,
            right - 9, bottom + (top - bottom) / 2 + 4,
            245, 204, 105, filled=True,
        )
        if self.required_plates > 1:
            spacing = (right - left) / (self.required_plates + 1)
            for index in range(self.required_plates):
                x = left + spacing * (index + 1)
                color = (100, 220, 147) if index < self.pressed_count else (232, 179, 84)
                draw_rectangle(x - 2, top - 14, x + 2, top - 8, *color, filled=True)


class PressurePlate:
    def __init__(self, object_id, target_id, rect, style='standard',
                 requires_echo=False):
        self.object_id = object_id
        self.target_id = target_id
        self.rect = rect
        self.is_pressed = False
        self.signal_marks = 0
        self.style = style
        self.requires_echo = requires_echo

    def update(self, actors):
        left, _, right, top = self.rect
        self.is_pressed = any(
            actor.grounded
            and (not self.requires_echo or getattr(actor, 'is_echo', False))
            and abs(actor.get_collision_box()[1] - top) <= 1
            and actor.get_collision_box()[2] > left
            and actor.get_collision_box()[0] < right
            for actor in actors
        )

    def draw(self, camera=None):
        if self.style == 'echo_pad':
            left, bottom, right, top = _screen_rect(self.rect, camera)
            width, height = right - left, top - bottom
            if self.is_pressed:
                main_color = (236, 190, 255)
                glow_alpha = 120
            else:
                main_color = (172, 99, 204)
                glow_alpha = 58
            SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
            draw_rectangle(left - 5, bottom - 5, right + 5, top + 6,
                           187, 111, 231, glow_alpha, filled=True)
            SDL_SetRenderDrawBlendMode(pico2d_core.renderer, 0)
            draw_rectangle(left, bottom - height * .20, right, top,
                           37, 43, 79, filled=True)
            draw_rectangle(left + 4, bottom, right - 4, top - 2,
                           *main_color, filled=True)
            for x in (left + 11, right - 11):
                draw_rectangle(x - 2, bottom + 1, x + 2, top - 2,
                               248, 224, 255, filled=True)
            draw_line(left + 19, bottom + 2, right - 19, bottom + 2,
                      247, 213, 255)
            return
        if getattr(self, 'images', None) is not None:
            sprite = self.images[1 if self.is_pressed else 0]
            _draw_sprite(sprite, self.rect, camera,
                         self.rect[2] - self.rect[0] + 20, 30, -10)
            left, bottom, right, _ = _screen_rect(self.rect, camera)
            _draw_signal_marks(left, bottom + 2, right, 4, self.signal_marks)
            return
        left, bottom, right, top = _screen_rect(self.rect, camera)
        draw_rectangle(left, bottom, right, top, 48, 55, 71, filled=True)
        if self.is_pressed:
            color = (100, 220, 147)
        else:
            color = (232, 179, 84)
        draw_rectangle(
            left + 3, bottom + 2, right - 3, top - 2,
            *color, filled=True,
        )
        _draw_signal_marks(left, bottom + 2, right, 4, self.signal_marks)


class EchoPlatform:
    """A translucent stepping stone that exists while an echo holds a plate."""

    def __init__(self, object_id, rect):
        self.object_id = object_id
        self.rect = tuple(rect)
        self.active = False
        self.animation_time = 0.0

    def update(self, active, dt):
        self.active = bool(active)
        self.animation_time += max(0.0, dt)

    def draw(self, camera=None):
        left, bottom, right, top = _screen_rect(self.rect, camera)
        scale = camera.zoom if camera is not None else 1.0
        pulse = (math.sin(self.animation_time * 4.0) + 1.0) * .5
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
        if not self.active:
            draw_rectangle(left, top - 3 * scale, right, top,
                           139, 224, 244, 34, filled=True)
            for x in range(int(left + 10 * scale), int(right), max(1, int(28 * scale))):
                draw_rectangle(x, top - 3 * scale, x + 7 * scale, top,
                               174, 235, 255, 90, filled=True)
            SDL_SetRenderDrawBlendMode(pico2d_core.renderer, 0)
            return
        glow = int(46 + 32 * pulse)
        draw_rectangle(left - 5 * scale, bottom - 5 * scale,
                       right + 5 * scale, top + 9 * scale,
                       92, 213, 255, glow, filled=True)
        draw_rectangle(left, bottom, right, top,
                       35, 116, 158, 224, filled=True)
        draw_rectangle(left + 3 * scale, top - 8 * scale,
                       right - 3 * scale, top - 2 * scale,
                       168, 242, 255, 238, filled=True)
        draw_rectangle(left + 8 * scale, bottom + 4 * scale,
                       right - 8 * scale, top - 10 * scale,
                       69, 174, 207, 118, filled=True)
        for index in range(1, 5):
            x = left + (right - left) * index / 5
            draw_line(x, bottom + 7 * scale, x, top - 10 * scale,
                      159, 232, 255, 145)
        SDL_SetRenderDrawBlendMode(pico2d_core.renderer, 0)
