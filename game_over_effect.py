import ctypes
import os

import pico2d
from pico2d import draw_rectangle, load_font


class GameOverEffect:
    WIDTH = 1280
    HEIGHT = 720

    def __init__(self):
        fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
        korean_font = os.path.join(fonts_dir, 'malgun.ttf')
        if os.path.isfile(korean_font):
            font_path = korean_font
            self.heading_label = '게임 오버'
            self.message_label = '스테이지를 다시 시작합니다'
        else:
            font_path = os.path.join(fonts_dir, 'arial.ttf')
            self.heading_label = 'GAME OVER'
            self.message_label = 'RESTARTING STAGE...'
        self.heading = load_font(font_path, 42)
        self.message = load_font(font_path, 22)

    def draw(self, width, height, elapsed):
        renderer = pico2d.draw_rectangle.__globals__.get('renderer')
        if renderer is None:
            raise RuntimeError('Open the Pico2D canvas before drawing the game-over effect.')

        previous_mode = ctypes.c_long()
        if pico2d.SDL_GetRenderDrawBlendMode(
            renderer,
            ctypes.byref(previous_mode),
        ) != 0:
            raise RuntimeError('Could not read the renderer blend mode.')
        if pico2d.SDL_SetRenderDrawBlendMode(
            renderer,
            pico2d.SDL_BLENDMODE_BLEND,
        ) != 0:
            raise RuntimeError('Could not enable alpha blending for the game-over effect.')

        try:
            pulse = (elapsed * 5) % 1
            overlay_alpha = 105 + round(35 * (1 - abs(pulse * 2 - 1)))
            draw_rectangle(
                0, 0, width, height, 45, 5, 14, overlay_alpha, filled=True,
            )

            border = 8 + round(12 * min(elapsed / 0.5, 1))
            draw_rectangle(0, 0, width, border, 220, 48, 65, 220, filled=True)
            draw_rectangle(
                0, height - border, width, height,
                220, 48, 65, 220, filled=True,
            )
            draw_rectangle(
                0, border, border, height - border,
                220, 48, 65, 220, filled=True,
            )
            draw_rectangle(
                width - border, border, width, height - border,
                220, 48, 65, 220, filled=True,
            )

            panel_width = min(560, width - 48)
            panel_height = 176
            left = (width - panel_width) / 2
            bottom = (height - panel_height) / 2
            draw_rectangle(
                left, bottom, left + panel_width, bottom + panel_height,
                25, 12, 24, 238, filled=True,
            )
            draw_rectangle(
                left, bottom, left + 6, bottom + panel_height,
                232, 73, 83, filled=True,
            )
            self.heading.draw(
                left + 34, bottom + 100, self.heading_label, (255, 229, 231),
            )
            self.message.draw(
                left + 34, bottom + 52, self.message_label, (224, 192, 198),
            )
        finally:
            if pico2d.SDL_SetRenderDrawBlendMode(
                renderer,
                previous_mode.value,
            ) != 0:
                raise RuntimeError('Could not restore the renderer blend mode.')
