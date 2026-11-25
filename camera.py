class Camera:
    def __init__(self, width, height, zoom=1.0):
        if width <= 0 or height <= 0:
            raise ValueError('Camera dimensions must be positive.')
        if zoom <= 0:
            raise ValueError('Camera zoom must be positive.')

        self.width = float(width)
        self.height = float(height)
        self.zoom = float(zoom)
        self.x = self.width / 2
        self.y = self.height / 2

    def follow(self, x, y, map_width, map_height):
        if map_width <= 0 or map_height <= 0:
            raise ValueError('Map dimensions must be positive.')

        self.zoom = max(
            self.zoom,
            self.width / map_width,
            self.height / map_height,
        )
        half_view_width = self.width / (2 * self.zoom)
        half_view_height = self.height / (2 * self.zoom)
        self.x = min(
            max(float(x), half_view_width),
            map_width - half_view_width,
        )
        self.y = min(
            max(float(y), half_view_height),
            map_height - half_view_height,
        )

    def world_to_screen(self, x, y):
        return (
            self.width / 2 + (x - self.x) * self.zoom,
            self.height / 2 + (y - self.y) * self.zoom,
        )

    def transform_size(self, size):
        return size * self.zoom


class OffsetCamera:
    """Apply a temporary screen-space offset without moving the game camera."""

    def __init__(self, camera, x, y):
        self.camera = camera
        self.offset_x = x
        self.offset_y = y

    def __getattr__(self, name):
        return getattr(self.camera, name)

    def world_to_screen(self, x, y):
        x, y = self.camera.world_to_screen(x, y)
        return x + self.offset_x, y + self.offset_y

    def transform_size(self, size):
        return self.camera.transform_size(size)
