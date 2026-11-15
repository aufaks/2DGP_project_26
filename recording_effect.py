import ctypes

import pico2d
from pico2d import draw_rectangle


_BAND_COUNT = 16
_BAND_WIDTH = 1
_BLUE = (25, 115, 255)
_OUTER_ALPHA = 150


def _renderer():
    # Pico2D exposes drawing helpers but keeps the renderer in their module globals.
    renderer = draw_rectangle.__globals__.get('renderer')
    if renderer is None:
        raise RuntimeError('Open the Pico2D canvas before drawing the recording effect.')
    return renderer


def _draw_bands(width, height):
    for band in range(_BAND_COUNT):
        blend = band / (_BAND_COUNT - 1)
        alpha = round(_OUTER_ALPHA * (1 - blend))
        inset = band * _BAND_WIDTH
        inner_left = inset
        inner_bottom = inset
        inner_right = width - inset
        inner_top = height - inset
        band_inner = inset + _BAND_WIDTH

        draw_rectangle(
            inner_left,
            inner_bottom,
            inner_right,
            band_inner,
            *_BLUE,
            alpha,
            filled=True,
        )
        draw_rectangle(
            inner_left,
            inner_top - _BAND_WIDTH,
            inner_right,
            inner_top,
            *_BLUE,
            alpha,
            filled=True,
        )
        draw_rectangle(
            inner_left,
            band_inner,
            band_inner,
            inner_top - _BAND_WIDTH,
            *_BLUE,
            alpha,
            filled=True,
        )
        draw_rectangle(
            inner_right - _BAND_WIDTH,
            band_inner,
            inner_right,
            inner_top - _BAND_WIDTH,
            *_BLUE,
            alpha,
            filled=True,
        )


def draw_recording_effect(width, height):
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
        raise RuntimeError('Could not enable alpha blending for the recording effect.')

    try:
        _draw_bands(width, height)
    finally:
        if pico2d.SDL_SetRenderDrawBlendMode(
            renderer,
            previous_mode.value,
        ) != 0:
            raise RuntimeError('Could not restore the renderer blend mode.')
