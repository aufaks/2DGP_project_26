import os
from pathlib import Path

from pico2d import load_font, load_image
from sdl2 import SDL_SetTextureColorMod, SDL_SetTextureScaleMode, SDL_ScaleModeLinear


def load_echo_slot_font():
    fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    font_path = os.path.join(fonts_dir, 'malgun.ttf')
    if not os.path.exists(font_path):
        font_path = os.path.join(fonts_dir, 'arial.ttf')
    return load_font(font_path, 12)


class EchoSlotUI:
    SIZE = 66
    CENTERS = (54, 132, 210)
    CENTER_Y = 58
    COLORS = ((78, 156, 220), (80, 196, 133), (161, 112, 218))
    RING_COLORS = ((105, 207, 255), (108, 255, 177), (215, 166, 255))
    RECORD_KEYS = ('i', 'o', 'p')
    PLAY_KEYS = ('j', 'k', 'l')
    RING_FRAME_SIZE = 128
    RING_STEPS = 60

    def __init__(self):
        root = Path(__file__).resolve().parent / 'sprite'
        self.base = load_image(str(root / 'echo_slot_base.png'))
        self.fill = load_image(str(root / 'echo_slot_fill.png'))
        self.ring = load_image(str(root / 'echo_slot_ring.png'))
        self.key_bg = load_image(str(root / 'echo_key_bg.png'))
        self.keys = {key: load_image(str(root / f'echo_key_{key}.png'))
                     for key in self.RECORD_KEYS + self.PLAY_KEYS}
        for image in self.keys.values():
            SDL_SetTextureScaleMode(image.texture, SDL_ScaleModeLinear)

    @staticmethod
    def _tinted(image, color, draw):
        try:
            SDL_SetTextureColorMod(image.texture, *color)
            draw()
        finally:
            SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def draw_slot(self, index, filled=False, progress=None):
        x, y, size = self.CENTERS[index], self.CENTER_Y, self.SIZE
        self.base.draw(x, y, size, size)
        if filled:
            self._tinted(self.fill, self.COLORS[index],
                         lambda: self.fill.draw(x, y, size, size))
            self.keys[self.PLAY_KEYS[index]].draw(x, y, 33, 33)
        if progress is not None:
            frame = max(0, min(self.RING_STEPS,
                               round(progress * self.RING_STEPS)))
            self._tinted(
                self.ring, self.RING_COLORS[index],
                lambda: self.ring.clip_draw(
                    frame * self.RING_FRAME_SIZE, 0, self.RING_FRAME_SIZE,
                    self.RING_FRAME_SIZE, x, y, size, size),
            )
        self.key_bg.draw(x, y - 32, 25, 25)
        self.keys[self.RECORD_KEYS[index]].draw(x, y - 32, 21, 21)

    def draw(self, recorder, echo):
        if recorder.is_recording:
            self.draw_slot(0, filled=False, progress=recorder.progress)
        elif echo is not None:
            self.draw_slot(0, filled=True, progress=echo.progress)
        else:
            self.draw_slot(0, filled=recorder.has_recording)
        self.draw_slot(1)
        self.draw_slot(2)
