import os
import math
import time
from pathlib import Path

from pico2d import load_font, load_image
from sdl2 import (SDL_SetTextureAlphaMod, SDL_SetTextureColorMod,
                  SDL_SetTextureScaleMode, SDL_ScaleModeLinear)


def load_echo_slot_font():
    fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    font_path = os.path.join(fonts_dir, 'malgun.ttf')
    if not os.path.exists(font_path):
        font_path = os.path.join(fonts_dir, 'arial.ttf')
    return load_font(font_path, 12)


class EchoSlotUI:
    SIZE = 78
    CENTERS = (62, 154, 246)
    CENTER_Y = 66
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
        self.panel = load_image(str(root / 'echo_slot_panel.png'))
        self.recording_icon = load_image(str(root / 'echo_recording_crystal.png'))
        self.particle = load_image(str(root / 'echo_slot_particle.png'))
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

    def draw_particles(self, index):
        now = time.monotonic()
        x, y = self.CENTERS[index], self.CENTER_Y
        try:
            SDL_SetTextureColorMod(self.particle.texture, *self.RING_COLORS[index])
            for offset, start_y, phase, size in ((-23, -12, 0.0, 14),
                                                 (-10, -25, .21, 11),
                                                 (4, -16, .43, 15),
                                                 (19, -5, .64, 12),
                                                 (0, 14, .82, 10)):
                progress = (now / 2.6 + phase) % 1.0
                opacity = round(230 * math.sin(math.pi * progress))
                SDL_SetTextureAlphaMod(self.particle.texture, opacity)
                self.particle.draw(x + offset + 4 * math.sin(progress * math.pi),
                                   y + start_y + 42 * progress, size, size)
        finally:
            SDL_SetTextureAlphaMod(self.particle.texture, 255)
            SDL_SetTextureColorMod(self.particle.texture, 255, 255, 255)

    def draw_slot(self, index, filled=False, progress=None, recording=False):
        x, y, size = self.CENTERS[index], self.CENTER_Y, self.SIZE
        self.base.draw(x, y, size, size)
        if filled or recording:
            self._tinted(self.fill, self.COLORS[index],
                         lambda: self.fill.draw(x, y, size, size))
        if filled and not recording:
            self.draw_particles(index)
        if filled:
            self.keys[self.PLAY_KEYS[index]].draw(x, y, 33, 33)
        if recording:
            icon_size = 35 + 3 * math.sin(time.monotonic() * 4)
            self.recording_icon.draw(x, y, icon_size, icon_size)
        if progress is not None:
            frame = max(0, min(self.RING_STEPS,
                               round(progress * self.RING_STEPS)))
            self._tinted(
                self.ring, self.RING_COLORS[index],
                lambda: self.ring.clip_draw(
                    frame * self.RING_FRAME_SIZE, 0, self.RING_FRAME_SIZE,
                    self.RING_FRAME_SIZE, x, y, size, size),
            )
        self.key_bg.draw(x, y - 38, 28, 28)
        self.keys[self.RECORD_KEYS[index]].draw(x, y - 38, 23, 23)

    def draw(self, recorder, echo):
        self.panel.draw(154, 64, 292, 106)
        if recorder.is_recording:
            self.draw_slot(0, progress=recorder.progress, recording=True)
        elif echo is not None:
            self.draw_slot(0, filled=True, progress=echo.progress)
        else:
            self.draw_slot(0, filled=recorder.has_recording)
        self.draw_slot(1)
        self.draw_slot(2)
