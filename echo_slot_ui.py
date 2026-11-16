import os

from pico2d import draw_rectangle, load_font


_PANEL_WIDTH = 200
_PANEL_HEIGHT = 88
_PANEL_LEFT = 12
_PANEL_BOTTOM = 12
_ICON_SIZE = 48
_ICON_GAP = 9
_ICON_INSET = 4
_ICON_BOTTOM_OFFSET = 27

_PANEL_COLOR = (22, 29, 43)
_ICON_BACKGROUND = (43, 52, 69)
_TEXT_COLOR = (239, 244, 255)
_MUTED_TEXT_COLOR = (135, 148, 169)
_RECORD_COLOR = (45, 145, 255)
_PLAYBACK_COLOR = (166, 112, 255)
_READY_COLOR = (65, 173, 255)
_LOCKED_COLOR = (58, 65, 79)


def load_echo_slot_font():
    fonts_dir = os.path.join(
        os.environ.get('WINDIR', r'C:\Windows'),
        'Fonts',
    )
    font_path = os.path.join(fonts_dir, 'malgun.ttf')
    if not os.path.exists(font_path):
        font_path = os.path.join(fonts_dir, 'arial.ttf')
    return load_font(font_path, 12)


def _draw_slot_icon(left, bottom, key_label, progress, color, font):
    right = left + _ICON_SIZE
    top = bottom + _ICON_SIZE
    draw_rectangle(left, bottom, right, top, *_ICON_BACKGROUND, filled=True)

    fill_height = round(
        (_ICON_SIZE - _ICON_INSET * 2) * max(0.0, min(progress, 1.0))
    )
    if fill_height:
        draw_rectangle(
            left + _ICON_INSET,
            bottom + _ICON_INSET,
            right - _ICON_INSET,
            bottom + _ICON_INSET + fill_height,
            *color,
            filled=True,
        )

    draw_rectangle(left, bottom, right, bottom + 2, 94, 110, 135, filled=True)
    draw_rectangle(left, top - 2, right, top, 94, 110, 135, filled=True)
    draw_rectangle(left, bottom + 2, left + 2, top - 2, 94, 110, 135, filled=True)
    draw_rectangle(right - 2, bottom + 2, right, top - 2, 94, 110, 135, filled=True)
    font.draw(left + 13, bottom + 18, key_label, _TEXT_COLOR)


def draw_echo_slot_ui(recorder, echo, font):
    left = _PANEL_LEFT
    bottom = _PANEL_BOTTOM
    draw_rectangle(
        left,
        bottom,
        left + _PANEL_WIDTH,
        bottom + _PANEL_HEIGHT,
        *_PANEL_COLOR,
        filled=True,
    )

    if recorder.is_recording:
        first_progress = recorder.progress
        first_color = _RECORD_COLOR
        first_status = '{:.1f}s'.format(recorder.remaining_seconds)
    elif echo is not None:
        first_progress = echo.progress
        first_color = _PLAYBACK_COLOR
        first_status = '{:.1f}s'.format(echo.remaining_seconds)
    elif recorder.has_recording:
        first_progress = 1.0
        first_color = _READY_COLOR
        first_status = '준비'
    else:
        first_progress = 0.0
        first_color = _ICON_BACKGROUND
        first_status = '빈칸'

    icon_bottom = bottom + _ICON_BOTTOM_OFFSET
    slot_lefts = [
        left + (
            _PANEL_WIDTH
            - (3 * _ICON_SIZE + 2 * _ICON_GAP)
        ) // 2 + index * (_ICON_SIZE + _ICON_GAP)
        for index in range(3)
    ]
    slots = (
        ('I/J', first_progress, first_color, first_status, _TEXT_COLOR),
        ('O/K', 0.0, _LOCKED_COLOR, '잠김', _MUTED_TEXT_COLOR),
        ('P/L', 0.0, _LOCKED_COLOR, '잠김', _MUTED_TEXT_COLOR),
    )

    for icon_left, slot in zip(slot_lefts, slots):
        key_label, progress, color, status, text_color = slot
        _draw_slot_icon(
            icon_left,
            icon_bottom,
            key_label,
            progress,
            color,
            font,
        )
        font.draw(icon_left + 8, bottom + 8, status, text_color)
