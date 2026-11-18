from pico2d import draw_rectangle


def _screen_rect(rect, camera):
    left, bottom, right, top = rect
    if camera is None:
        return left, bottom, right, top

    left, bottom = camera.world_to_screen(left, bottom)
    right, top = camera.world_to_screen(right, top)
    return round(left), round(bottom), round(right), round(top)


class Door:
    def __init__(self, object_id, rect):
        self.object_id = object_id
        self.rect = rect
        self.is_open = False

    def update(self, activated, actors):
        occupied = any(self._overlaps_actor(actor) for actor in actors)
        self.is_open = bool(activated) or (self.is_open and occupied)

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
        left, bottom, right, top = _screen_rect(self.rect, camera)
        draw_rectangle(left, bottom, right, top, 57, 48, 65, filled=True)

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


class PressurePlate:
    def __init__(self, object_id, target_id, rect):
        self.object_id = object_id
        self.target_id = target_id
        self.rect = rect
        self.is_pressed = False

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
