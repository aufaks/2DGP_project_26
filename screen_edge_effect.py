from pathlib import Path

from pico2d import load_image
from sdl2 import SDL_SetTextureColorMod


class ScreenEdgeEffect:
    def __init__(self):
        path = Path(__file__).resolve().parent / 'sprite' / 'screen_edge.png'
        self.image = load_image(str(path))

    def draw(self, width, height, color, opacity):
        opacity = max(0.0, min(1.0, opacity))
        try:
            SDL_SetTextureColorMod(self.image.texture, *color)
            self.image.opacify(opacity)
            self.image.draw(width / 2, height / 2, width, height)
        finally:
            SDL_SetTextureColorMod(self.image.texture, 255, 255, 255)
            self.image.opacify(1.0)
