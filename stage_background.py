import os

from pico2d import load_image


class StageBackground:
    def __init__(self, width, height):
        sprite_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'sprite',
        )
        self.image = load_image(os.path.join(sprite_dir, 'Background_Stage.png'))
        self.width = width
        self.height = height

    def update(self, dt):
        pass

    def draw(self, camera=None):
        draw_x = self.width / 2
        draw_y = self.height / 2
        draw_width = self.width
        draw_height = self.height

        if camera is not None:
            draw_x, draw_y = camera.world_to_screen(draw_x, draw_y)
            draw_width = camera.transform_size(draw_width)
            draw_height = camera.transform_size(draw_height)

        self.image.draw(draw_x, draw_y, draw_width, draw_height)
