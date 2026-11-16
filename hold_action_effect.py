import ctypes

import pico2d
from pico2d import draw_rectangle


_DURATION = 0.65
_BORDER_SIZE = 12
_COLORS = {
    'save': (70, 235, 135),
    'restore': (255, 170, 55),
}


def _renderer():
    renderer = draw_rectangle.__globals__.get('renderer')
    if renderer is None:
        raise RuntimeError('Open the Pico2D canvas before drawing the hold effect.')
    return renderer


def draw_hold_action_effect(width, height, action, elapsed):
    if action not in _COLORS:
        raise ValueError('Action must be "save" or "restore".')
    if elapsed < 0 or elapsed >= _DURATION:
        return

    alpha = round(220 * (1 - elapsed / _DURATION))
    color = _COLORS[action]
    renderer = _renderer()
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
        raise RuntimeError('Could not enable alpha blending for the hold effect.')

    try:
        border = min(_BORDER_SIZE, width // 2, height // 2)
        draw_rectangle(0, 0, width, border, *color, alpha, filled=True)
        draw_rectangle(0, height - border, width, height, *color, alpha, filled=True)
        draw_rectangle(0, border, border, height - border, *color, alpha, filled=True)
        draw_rectangle(
            width - border,
            border,
            width,
            height - border,
            *color,
            alpha,
            filled=True,
        )
    finally:
        if pico2d.SDL_SetRenderDrawBlendMode(
            renderer,
            previous_mode.value,
        ) != 0:
            raise RuntimeError('Could not restore the renderer blend mode.')
