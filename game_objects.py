from pico2d import draw_rectangle


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
    def __init__(self, object_id, rect):
        self.object_id = object_id
        self.rect = rect

    def draw(self, camera=None):
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
    def __init__(self, object_id, target_id, rect):
        self.object_id = object_id
        self.target_id = target_id
        self.rect = rect
        self.is_pressed = False
        self.signal_marks = 0

    def update(self, actors):
        left, _, right, top = self.rect
        self.is_pressed = any(
            actor.grounded
            and abs(actor.get_collision_box()[1] - top) <= 1
            and actor.get_collision_box()[2] > left
            and actor.get_collision_box()[0] < right
            for actor in actors
        )

    def draw(self, camera=None):
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
