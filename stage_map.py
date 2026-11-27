from pathlib import Path
import json

from pico2d import draw_circle, draw_line, draw_rectangle
from pico2d import pico2d as pico2d_core
from sdl2 import SDL_BLENDMODE_BLEND, SDL_SetRenderDrawBlendMode

from asset_cache import load_image
from game_objects import Door, EchoPlatform, PressurePlate, StageExit


class StageMap:
    """A screen-sized illustrated stage with pixel-precise collision geometry."""

    def __init__(self, stage_path):
        self.path = Path(stage_path).resolve()
        with self.path.open(encoding='utf-8') as file:
            data = json.load(file)
        self.background_path = (self.path.parent / data['background']).resolve()
        self.pixel_width, self.pixel_height = data['size']
        self.player_spawn = tuple(data['player_spawn'])
        self.character_scale = data.get('character_scale', 1.0)
        self.collision_rects = [tuple(rect) for rect in data.get('collision_rects', [])]
        self.platform_rects = []
        self.slope_tiles = [tuple(slope) for slope in data.get('slopes', [])]
        self.doors = {}
        self.echo_platforms = {}
        self.pressure_plates = []
        self.echo_devices = []
        self.stage_exits = []
        self.echo_notice_seconds = 0.0
        self.animation_time = 0.0
        self.images = []
        for item in data.get('images', []):
            image = load_image(str((self.path.parent / item['path']).resolve()))
            self.images.append((image, tuple(item['rect'])))
        ids = set()
        for item in data.get('platforms', []):
            object_id = item['id']
            if object_id in ids:
                raise ValueError(f'Duplicate stage object id: {object_id}')
            ids.add(object_id)
            if item.get('type') == 'EchoPlatform':
                self.echo_platforms[object_id] = EchoPlatform(
                    object_id, item['rect'])
                if item.get('sprite'):
                    self.echo_platforms[object_id].image = load_image(
                        str((self.path.parent / item['sprite']).resolve()))
                    if item.get('inactive_sprite'):
                        self.echo_platforms[object_id].inactive_image = load_image(
                            str((self.path.parent / item['inactive_sprite']).resolve()))
            else:
                raise ValueError(f"Unknown platform type: {item.get('type')}")
        for item in data.get('objects', []):
            if item['type'] == 'EchoDevice':
                continue
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
                plate = PressurePlate(
                    object_id, item['target_id'], rect,
                    style=item.get('style', 'standard'),
                    requires_echo=item.get('requires_echo', False),
                    extra_target_ids=item.get('extra_target_ids', ()))
                if item.get('sprites'):
                    idle, pressed = item['sprites']
                    plate.images = tuple(
                        load_image(str((self.path.parent / path).resolve()))
                        for path in (idle, pressed))
                self.pressure_plates.append(plate)
            elif kind == 'StageExit':
                self.stage_exits.append(StageExit(
                    object_id, rect, item.get('style', 'arch')))
            else:
                raise ValueError(f'Unknown stage object type: {kind}')
            if kind == 'StageExit' and item.get('sprite'):
                image = load_image(str((self.path.parent / item['sprite']).resolve()))
                self.stage_exits[-1].stage_image = image
            if kind == 'StageExit' and item.get('glow_sprite'):
                self.stage_exits[-1].glow_image = load_image(
                    str((self.path.parent / item['glow_sprite']).resolve()))
        for plate in self.pressure_plates:
            for target_id in plate.target_ids:
                if target_id in self.doors:
                    plate.signal_marks = self.doors[target_id].signal_marks
                elif target_id not in self.echo_platforms:
                    raise ValueError(f'Unknown pressure plate target: {target_id}')
        self.echo_unlocked = True
        self.interact_prompt = None
        if data.get('objects'):
            sprite_dir = Path(__file__).resolve().parent / 'sprite'
            names = ('plate_idle', 'plate_pressed', 'door_closed',
                     'door_open', 'stage_exit')
            assets = {name: load_image(str(sprite_dir / f'{name}.png'))
                      for name in names}
            for door in self.doors.values():
                door.images = (assets['door_closed'], assets['door_open'])
            for plate in self.pressure_plates:
                if plate.images is None:
                    plate.images = (assets['plate_idle'], assets['plate_pressed'])
            for stage_exit in self.stage_exits:
                stage_exit.image = assets['stage_exit']

    def update(self, dt):
        self.animation_time += dt
        self.echo_notice_seconds = max(0.0, self.echo_notice_seconds - dt)
        for stage_exit in self.stage_exits:
            stage_exit.update(dt)

    def update_mechanisms(self, actors, dt=1 / 60):
        actors = tuple(actors)
        for plate in self.pressure_plates:
            plate.update(actors)
        for object_id, platform in self.echo_platforms.items():
            activated = any(plate.is_pressed and object_id in plate.target_ids
                            for plate in self.pressure_plates)
            platform.update(activated, dt)
        self.platform_rects = [
            platform.rect for platform in self.echo_platforms.values()
            if platform.active
        ]
        for object_id, door in self.doors.items():
            pressed = sum(plate.is_pressed and object_id in plate.target_ids
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
        if not self.images:
            for rect in self.collision_rects:
                self._draw_ruin_geometry(rect, camera)
        for obj in (*self.doors.values(), *self.pressure_plates,
                    *self.echo_devices, *self.stage_exits):
            obj.draw(camera)
        for platform in self.echo_platforms.values():
            platform.draw(camera)

    def _draw_ruin_geometry(self, rect, camera):
        left, bottom, right, top = rect
        if camera is not None:
            left, bottom = camera.world_to_screen(left, bottom)
            right, top = camera.world_to_screen(right, top)
            scale = camera.zoom
        else:
            scale = 1.0
        width, height = right - left, top - bottom
        if width <= 0 or height <= 0:
            return

        is_wall = height > width * .68
        draw_rectangle(left, bottom, right, top, 44, 57, 91, filled=True)
        if is_wall:
            block_h, block_w = 42 * scale, 64 * scale
            row, y = 0, bottom + 4 * scale
            while y < top - 18 * scale:
                offset = 0 if row % 2 == 0 else block_w / 2
                draw_line(left, y, right, y, 71, 84, 119, 170)
                x = left + offset
                while x < right:
                    if x > left + 2:
                        draw_line(x, y, x, min(top, y + block_h),
                                  67, 79, 110, 145)
                    x += block_w
                y += block_h
                row += 1
            draw_rectangle(left, bottom, right, bottom + 12 * scale,
                           27, 37, 67, filled=True)
            draw_rectangle(left, top - 11 * scale, right, top,
                           165, 178, 202, filled=True)
            draw_line(left + 5 * scale, top - 13 * scale,
                      right - 3 * scale, top - 13 * scale,
                      222, 211, 207, 210)
            for x, y in ((left + width * .20, bottom + height * .30),
                         (left + width * .72, bottom + height * .68)):
                draw_circle(x, y, max(1, int(round(3.5 * scale))),
                            81, 207, 192, 150, filled=True)
                draw_line(x, y - 12 * scale, x, y - 4 * scale,
                          86, 193, 184, 160)
            return

        top_h = min(22 * scale, height * .20)
        draw_rectangle(left, bottom, right, bottom + height * .40,
                       35, 46, 76, filled=True)
        draw_rectangle(left + 3 * scale, bottom + height * .40,
                       right - 2 * scale, top - top_h,
                       62, 78, 116, filled=True)
        draw_rectangle(left, top - top_h, right, top,
                       183, 184, 199, filled=True)
        draw_rectangle(left + 3 * scale, top - 5 * scale,
                       right - 3 * scale, top - 2 * scale,
                       225, 215, 201, filled=True)
        draw_line(left + 4 * scale, top - top_h - 1 * scale,
                  right - 3 * scale, top - top_h - 1 * scale,
                  104, 123, 155, 220)
        tile_w = 48 * scale
        x, index = left + tile_w, 0
        while x < right - 3 * scale:
            seam_y = top - top_h + (3 if index % 2 else 7) * scale
            draw_line(x, bottom + height * .40, x, seam_y,
                      42, 57, 88, 145)
            draw_line(x + 3 * scale, seam_y, x + tile_w * .60, seam_y,
                      220, 205, 193, 150)
            x += tile_w
            index += 1
        for x in (left + width * .22, left + width * .78):
            draw_circle(x, bottom + height * .24,
                        max(1, int(round(3 * scale))),
                        60, 175, 184, 190, filled=True)

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
            y = next_y

        max_x = self.pixel_width - half_width
        x = self.pixel_width / 2 if max_x < half_width else \
            min(max(x, half_width), max_x)
        grounded = landed or self.is_supported(x, y, width)
        return x, y, grounded, hit_ceiling
