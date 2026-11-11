import csv
import json
from pathlib import Path

from pico2d import load_image


_GID_MASK = 0x0FFFFFFF
_FLIP_HORIZONTAL = 0x80000000
_FLIP_VERTICAL = 0x40000000
_FLIP_DIAGONAL = 0x20000000
_FLIP_HEX_120 = 0x10000000


class TiledMap:
    def __init__(self, map_path):
        self.path = Path(map_path).resolve()
        self.data = self._read_json(self.path)
        if self.data.get('orientation') != 'orthogonal':
            raise ValueError('Only orthogonal Tiled maps are supported.')
        if self.data.get('infinite', False):
            raise ValueError('Infinite Tiled maps are not supported.')

        self.width = self.data['width']
        self.height = self.data['height']
        self.tile_width = self.data['tilewidth']
        self.tile_height = self.data['tileheight']
        self.pixel_width = self.width * self.tile_width
        self.pixel_height = self.height * self.tile_height
        self.tile_layers = []
        self.collision_rects = []
        self.player_spawn = None

        self.tilesets = self._load_tilesets()
        self._load_layers()

    @staticmethod
    def _read_json(path):
        try:
            with path.open(encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError as error:
            raise FileNotFoundError(f'Tiled map resource not found: {path}') from error
        except json.JSONDecodeError as error:
            raise ValueError(f'Invalid Tiled JSON in {path}: {error}') from error

    def _load_tilesets(self):
        tilesets = []
        for reference in self.data.get('tilesets', []):
            tileset_data = reference
            if 'source' in reference:
                source_path = (self.path.parent / reference['source']).resolve()
                tileset_data = self._read_json(source_path)
                tileset_data = dict(tileset_data)
            else:
                tileset_data = dict(reference)

            if tileset_data['tilewidth'] != self.tile_width or \
                    tileset_data['tileheight'] != self.tile_height:
                raise ValueError(
                    'Tileset tile dimensions must match the map tile dimensions.'
                )

            image_path = (source_path.parent / tileset_data['image']).resolve() \
                if 'source' in reference else \
                (self.path.parent / tileset_data['image']).resolve()
            tileset_data['image_object'] = load_image(str(image_path))
            tileset_data['firstgid'] = reference['firstgid']
            if tileset_data.get('columns', 0) <= 0:
                raise ValueError(f'Tileset must define a positive columns value: {image_path}')
            tilesets.append(tileset_data)

        return sorted(tilesets, key=lambda tileset: tileset['firstgid'])

    def _load_layers(self):
        for layer in self.data.get('layers', []):
            if layer['type'] == 'tilelayer':
                if not layer.get('visible', True):
                    continue
                if layer.get('chunks'):
                    raise ValueError('Chunked Tiled layers are not supported.')
                self.tile_layers.append((layer, self._layer_data(layer)))
            elif layer['type'] == 'objectgroup':
                self._load_object_layer(layer)
            elif layer['type'] == 'group':
                raise ValueError('Nested Tiled group layers are not supported.')

    def _layer_data(self, layer):
        values = layer.get('data')
        if isinstance(values, str):
            if layer.get('encoding') != 'csv':
                raise ValueError(
                    f"Unsupported encoding in Tiled layer '{layer.get('name', '')}'."
                )
            values = [
                int(value)
                for row in csv.reader(values.splitlines())
                for value in row
            ]
        if not isinstance(values, list):
            raise ValueError(
                f"Tile layer '{layer.get('name', '')}' must have an uncompressed data array."
            )
        if len(values) != layer['width'] * layer['height']:
            raise ValueError(
                f"Tile layer '{layer.get('name', '')}' data size does not match its dimensions."
            )
        return values

    def _load_object_layer(self, layer):
        offset_x = layer.get('offsetx', 0) + layer.get('x', 0) * self.tile_width
        offset_y = layer.get('offsety', 0) + layer.get('y', 0) * self.tile_height

        for obj in layer.get('objects', []):
            x = obj.get('x', 0) + offset_x
            y = obj.get('y', 0) + offset_y
            width = obj.get('width', 0)
            height = obj.get('height', 0)

            if layer.get('name') == 'Collision':
                if any(key in obj for key in ('ellipse', 'point', 'polygon', 'polyline', 'gid')):
                    raise ValueError(
                        'Collision layer supports rectangle objects only.'
                    )
                if obj.get('rotation', 0) != 0 or width <= 0 or height <= 0:
                    raise ValueError(
                        'Collision rectangles must have positive size and no rotation.'
                    )
                bottom = self.pixel_height - y - height
                self.collision_rects.append(
                    (x, bottom, x + width, bottom + height)
                )
            elif obj.get('name') == 'PlayerSpawn':
                if self.player_spawn is not None:
                    raise ValueError('Tiled map can define only one PlayerSpawn object.')
                self.player_spawn = (
                    x + width / 2,
                    self.pixel_height - y - height / 2,
                )

    def update(self, dt):
        pass

    def draw(self, camera=None):
        for layer, values in self.tile_layers:
            layer_width = layer['width']
            offset_x = layer.get('offsetx', 0) + layer.get('x', 0) * self.tile_width
            offset_y = layer.get('offsety', 0) + layer.get('y', 0) * self.tile_height

            for index, raw_gid in enumerate(values):
                if raw_gid == 0:
                    continue
                gid = raw_gid & _GID_MASK
                tileset = self._find_tileset(gid)
                tile_id = gid - tileset['firstgid']
                columns = tileset['columns']
                margin = tileset.get('margin', 0)
                spacing = tileset.get('spacing', 0)
                source_x = margin + (tile_id % columns) * (
                    tileset['tilewidth'] + spacing
                )
                source_top = margin + (tile_id // columns) * (
                    tileset['tileheight'] + spacing
                )
                source_y = tileset['image_object'].h - source_top - self.tile_height

                flags = raw_gid & ~_GID_MASK
                if flags & (_FLIP_DIAGONAL | _FLIP_HEX_120):
                    raise ValueError(
                        'Diagonal and hexagonal Tiled tile transforms are not supported.'
                    )
                flip = ''
                if flags & _FLIP_HORIZONTAL:
                    flip += 'h'
                if flags & _FLIP_VERTICAL:
                    flip += 'v'

                column = index % layer_width
                row = index // layer_width
                x = column * self.tile_width + self.tile_width / 2 + offset_x
                y = self.pixel_height - (
                    row * self.tile_height + self.tile_height / 2 + offset_y
                )
                draw_width = self.tile_width
                draw_height = self.tile_height
                if camera is not None:
                    x, y = camera.world_to_screen(x, y)
                    draw_width = camera.transform_size(draw_width)
                    draw_height = camera.transform_size(draw_height)
                tileset['image_object'].clip_composite_draw(
                    source_x,
                    source_y,
                    self.tile_width,
                    self.tile_height,
                    0,
                    flip,
                    x,
                    y,
                    draw_width,
                    draw_height,
                )

    def _find_tileset(self, gid):
        for tileset in reversed(self.tilesets):
            if gid >= tileset['firstgid']:
                tile_id = gid - tileset['firstgid']
                if tile_id < tileset['tilecount']:
                    return tileset
                break
        raise ValueError(f'Tiled tile gid {gid} does not belong to a loaded tileset.')

    def is_supported(self, x, y, width, tolerance=1.0):
        left = x - width / 2
        right = x + width / 2
        for rect_left, rect_bottom, rect_right, rect_top in self.collision_rects:
            if abs(y - rect_top) <= tolerance and \
                    right > rect_left and left < rect_right:
                return True
        return False

    def move_actor(self, x, y, width, height, dx, dy):
        half_width = width / 2

        if dx:
            next_x = x + dx
            for left, bottom, right, top in self.collision_rects:
                if y < top and y + height > bottom:
                    if dx > 0 and x + half_width <= left and \
                            next_x + half_width > left:
                        next_x = min(next_x, left - half_width)
                    elif dx < 0 and x - half_width >= right and \
                            next_x - half_width < right:
                        next_x = max(next_x, right + half_width)
            max_x = self.pixel_width - half_width
            x = self.pixel_width / 2 if max_x < half_width else \
                min(max(next_x, half_width), max_x)

        landed = False
        hit_ceiling = False
        hit_bottom = False
        if dy:
            next_y = y + dy
            for left, bottom, right, top in self.collision_rects:
                if x + half_width > left and x - half_width < right:
                    if dy < 0 and y >= top and next_y < top:
                        next_y = max(next_y, top)
                        landed = True
                    elif dy > 0 and y + height <= bottom and \
                            next_y + height > bottom:
                        next_y = min(next_y, bottom - height)
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
