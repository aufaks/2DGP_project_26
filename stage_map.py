from pathlib import Path
import json

from pico2d import load_image, draw_rectangle

from game_objects import Door, EchoDevice, PressurePlate, StageExit


class StageMap:
    """A screen-sized illustrated stage with pixel-precise collision geometry."""

    def __init__(self, stage_path):
        self.path = Path(stage_path).resolve()
        with self.path.open(encoding='utf-8') as file:
            data = json.load(file)
        self.background_path = (self.path.parent / data['background']).resolve()
        self.pixel_width, self.pixel_height = data['size']
        self.player_spawn = tuple(data['player_spawn'])
        self.collision_rects = [tuple(rect) for rect in data.get('collision_rects', [])]
        self.platform_rects = []
        self.slope_tiles = [tuple(slope) for slope in data.get('slopes', [])]
        self.doors = {}
        self.pressure_plates = []
        self.echo_devices = []
        self.stage_exits = []
        self.echo_notice_seconds = 0.0
        self.images = []
        for item in data.get('images', []):
            image = load_image(str((self.path.parent / item['path']).resolve()))
            self.images.append((image, tuple(item['rect'])))
        ids = set()
        for item in data.get('objects', []):
            object_id = item['id']
            if object_id in ids:
                raise ValueError(f'Duplicate stage object id: {object_id}')
            ids.add(object_id)
            rect = tuple(item['rect'])
            kind = item['type']
            if kind == 'Door':
                self.doors[object_id] = Door(
                    object_id, rect, item.get('required_plates', 1),
                    item.get('latch', False), item.get('signal_marks', 0))
            elif kind == 'PressurePlate':
                self.pressure_plates.append(
                    PressurePlate(object_id, item['target_id'], rect))
            elif kind == 'EchoDevice':
                self.echo_devices.append(EchoDevice(
                    object_id, rect, item.get('interaction_range', 64)))
            elif kind == 'StageExit':
                self.stage_exits.append(StageExit(object_id, rect))
            else:
                raise ValueError(f'Unknown stage object type: {kind}')
        for plate in self.pressure_plates:
            if plate.target_id not in self.doors:
                raise ValueError(f'Unknown door: {plate.target_id}')
            plate.signal_marks = self.doors[plate.target_id].signal_marks
        self.echo_unlocked = not self.echo_devices
        self.interact_prompt = None
        if data.get('objects'):
            sprite_dir = Path(__file__).resolve().parent / 'sprite'
            names = ('plate_idle', 'plate_pressed', 'door_closed',
                     'door_open', 'echo_device', 'stage_exit', 'interact_prompt')
            assets = {name: load_image(str(sprite_dir / f'{name}.png'))
                      for name in names}
            self.interact_prompt = assets['interact_prompt']
            for door in self.doors.values():
                door.images = (assets['door_closed'], assets['door_open'])
            for plate in self.pressure_plates:
                plate.images = (assets['plate_idle'], assets['plate_pressed'])
            for device in self.echo_devices:
                device.image = assets['echo_device']
            for stage_exit in self.stage_exits:
                stage_exit.image = assets['stage_exit']

    def update(self, dt):
        self.echo_notice_seconds = max(0.0, self.echo_notice_seconds - dt)

    def collect_echo_device(self, actor):
        if self.echo_unlocked:
            return False
        for device in self.echo_devices:
            if device.collect(actor):
                self.echo_unlocked = True
                self.echo_notice_seconds = 4.0
                return True
        return False

    def draw_interaction_ui(self, actor, font, camera):
        if self.echo_unlocked or self.interact_prompt is None:
            return
        for device in self.echo_devices:
            if device.can_collect(actor):
                left, _, right, top = device.rect
                x, y = camera.world_to_screen((left + right) / 2, top + 72)
                self.interact_prompt.clip_composite_draw(
                    0, 0, self.interact_prompt.w, self.interact_prompt.h,
                    0, '', x, y, camera.transform_size(76),
                    camera.transform_size(36))

    def update_mechanisms(self, actors):
        actors = tuple(actors)
        for plate in self.pressure_plates:
            plate.update(actors)
        for object_id, door in self.doors.items():
            pressed = sum(plate.is_pressed and plate.target_id == object_id
                          for plate in self.pressure_plates)
            door.update(pressed, actors)

    def draw(self, camera=None):
        for image, (left, bottom, right, top) in self.images:
            x, y = (left + right) / 2, (bottom + top) / 2
            width, height = right - left, top - bottom
            if camera is not None:
                x, y = camera.world_to_screen(x, y)
                width, height = camera.transform_size(width), camera.transform_size(height)
            image.draw(x, y, width, height)
        for rect in self.collision_rects if not self.images else ():
            left, bottom, right, top = rect
            if camera is not None:
                left, bottom = camera.world_to_screen(left, bottom)
                right, top = camera.world_to_screen(right, top)
            draw_rectangle(left, bottom, right, top, 60, 104, 112, filled=True)
            draw_rectangle(left, top - 9, right, top, 223, 197, 146, filled=True)
        for obj in (*self.doors.values(), *self.pressure_plates,
                    *self.echo_devices, *self.stage_exits):
            obj.draw(camera)

    @property
    def solid_rects(self):
        return self.collision_rects + self.platform_rects + [
            door.rect for door in self.doors.values() if not door.is_open
        ]

    def _slope_surface_at(self, x):
        surfaces = []
        for left, bottom, right, top, slope_type in self.slope_tiles:
            if left <= x <= right:
                ratio = (x - left) / (right - left)
                surface = (
                    bottom + ratio * (top - bottom)
                    if slope_type == 'SlopeUpRight'
                    else top - ratio * (top - bottom)
                )
                surfaces.append(surface)
        return max(surfaces) if surfaces else None

    def _slope_connects_to_platform(self, next_x, direction, rect):
        if rect not in self.platform_rects:
            return False

        left, _, right, top = rect
        for slope_left, _, slope_right, slope_top, slope_type in self.slope_tiles:
            if abs(top - slope_top) > 1:
                continue
            if direction > 0 and slope_type == 'SlopeUpRight' \
                    and abs(slope_right - left) <= 1 \
                    and slope_left <= next_x <= slope_right:
                return True
            if direction < 0 and slope_type == 'SlopeUpLeft' \
                    and abs(slope_left - right) <= 1 \
                    and slope_left <= next_x <= slope_right:
                return True
        return False

    def _slope_transition_surface(self, previous_x, x, direction):
        for slope_left, _, slope_right, slope_top, slope_type in self.slope_tiles:
            if direction > 0 and slope_type == 'SlopeUpRight' \
                    and previous_x <= slope_right <= x:
                touches_platform = any(
                    abs(left - slope_right) <= 1
                    and abs(top - slope_top) <= 1
                    for left, _, _, top in self.platform_rects
                )
                if touches_platform:
                    return slope_top
            if direction < 0 and slope_type == 'SlopeUpLeft' \
                    and x <= slope_left <= previous_x:
                touches_platform = any(
                    abs(right - slope_left) <= 1
                    and abs(top - slope_top) <= 1
                    for _, _, right, top in self.platform_rects
                )
                if touches_platform:
                    return slope_top
        return None

    def is_supported(self, x, y, width, tolerance=1.0):
        left = x - width / 2
        right = x + width / 2
        for rect_left, rect_bottom, rect_right, rect_top in self.solid_rects:
            if abs(y - rect_top) <= tolerance and \
                    right > rect_left and left < rect_right:
                return True
        slope_surface = self._slope_surface_at(x)
        return slope_surface is not None and abs(y - slope_surface) <= tolerance

    def move_actor(self, x, y, width, height, dx, dy):
        half_width = width / 2
        solid_rects = self.solid_rects
        was_supported = self.is_supported(x, y, width)

        if dx:
            previous_x = x
            next_x = x + dx
            for left, bottom, right, top in solid_rects:
                if y < top and y + height > bottom:
                    if dx > 0 and x + half_width <= left and \
                            next_x + half_width > left:
                        if not (was_supported and self._slope_connects_to_platform(
                                next_x,
                                1,
                                (left, bottom, right, top),
                        )):
                            next_x = min(next_x, left - half_width)
                    elif dx < 0 and x - half_width >= right and \
                            next_x - half_width < right:
                        if not (was_supported and self._slope_connects_to_platform(
                                next_x,
                                -1,
                                (left, bottom, right, top),
                        )):
                            next_x = max(next_x, right + half_width)
            max_x = self.pixel_width - half_width
            x = self.pixel_width / 2 if max_x < half_width else \
                min(max(next_x, half_width), max_x)
            if was_supported:
                slope_surface = self._slope_surface_at(x)
                if slope_surface is not None and \
                        abs(slope_surface - y) <= abs(dx) + 1:
                    y = slope_surface
                elif slope_surface is None:
                    transition_surface = self._slope_transition_surface(
                        previous_x,
                        x,
                        1 if dx > 0 else -1,
                    )
                    if transition_surface is not None and \
                            abs(transition_surface - y) <= abs(dx) + 1:
                        y = transition_surface

        landed = False
        hit_ceiling = False
        hit_bottom = False
        if dy:
            next_y = y + dy
            for left, bottom, right, top in solid_rects:
                if x + half_width > left and x - half_width < right:
                    if dy < 0 and y >= top and next_y < top:
                        next_y = max(next_y, top)
                        landed = True
                    elif dy > 0 and y + height <= bottom and \
                            next_y + height > bottom:
                        next_y = min(next_y, bottom - height)
                        hit_ceiling = True
            slope_surface = self._slope_surface_at(x)
            if slope_surface is not None:
                if dy < 0 and y >= slope_surface and \
                        next_y <= slope_surface:
                    next_y = max(next_y, slope_surface)
                    landed = True
                elif dy > 0 and y + height <= slope_surface and \
                        next_y + height > slope_surface:
                    next_y = min(next_y, slope_surface - height)
                    hit_ceiling = True
            max_y = self.pixel_height - height
            if max_y < 0:
                y = self.pixel_height / 2 - height / 2
                hit_ceiling = dy > 0
                hit_bottom = dy < 0
            else:
                if next_y < 0:
                    next_y = 0
                    hit_bottom = dy < 0
                if next_y > max_y:
                    next_y = max_y
                    hit_ceiling = dy > 0
                y = next_y

        max_x = self.pixel_width - half_width
        x = self.pixel_width / 2 if max_x < half_width else \
            min(max(x, half_width), max_x)
        max_y = self.pixel_height - height
        y = self.pixel_height / 2 - height / 2 if max_y < 0 else \
            min(max(y, 0), max_y)
        grounded = landed or hit_bottom or self.is_supported(x, y, width)
        return x, y, grounded, hit_ceiling
