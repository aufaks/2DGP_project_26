"""Sprite sheet animation viewer for sprite/mc_run.png.

Run with: python animation_viewer.py

Click a frame in the sheet to select it. Use Left/Right to step frames,
Space to pause, +/- to adjust playback speed, and G to toggle the grid.
"""

import os
import time

from pico2d import *


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_PATH = os.path.join(BASE_DIR, 'sprite', 'mc_run.png')

# mc_run.png is a horizontal strip of 8 square frames.
COLUMNS = 8
ROWS = 1
FPS = 8.0

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 760
SHEET_SCALE = 0.38
SHEET_X = 410
SHEET_Y = 450
PREVIEW_X = 1010
PREVIEW_Y = 360
PREVIEW_SIZE = 320


def draw_label(font, text, x, y, color=(35, 42, 55)):
    font.draw(x, y, text, color)


def main():
    global running

    open_canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    sheet = load_image(SPRITE_PATH)
    sheet_width = sheet.w * SHEET_SCALE
    sheet_height = sheet.h * SHEET_SCALE
    preview_width = PREVIEW_SIZE
    preview_height = PREVIEW_SIZE * sheet.h / sheet.w * COLUMNS
    font_path = os.path.join(BASE_DIR, 'ENfont.ttf')
    if not os.path.exists(font_path):
        font_path = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf')
    font = load_font(font_path, 18)

    selected_frame = 0
    playing = True
    show_grid = True
    fps = FPS
    accumulator = 0.0
    last_time = time.perf_counter()
    running = True

    while running:
        now = time.perf_counter()
        dt = min(now - last_time, 0.1)
        last_time = now

        for event in get_events():
            if event.type == SDL_QUIT:
                running = False
            elif event.type == SDL_KEYDOWN:
                if event.key == SDLK_ESCAPE:
                    running = False
                elif event.key == SDLK_SPACE:
                    playing = not playing
                elif event.key == SDLK_g:
                    show_grid = not show_grid
                elif event.key in (SDLK_LEFT, SDLK_a):
                    selected_frame = (selected_frame - 1) % COLUMNS
                    accumulator = 0.0
                elif event.key in (SDLK_RIGHT, SDLK_d):
                    selected_frame = (selected_frame + 1) % COLUMNS
                    accumulator = 0.0
                elif event.key in (SDLK_EQUALS, SDLK_PLUS, SDLK_KP_PLUS):
                    fps = min(30.0, fps + 1.0)
                elif event.key in (SDLK_MINUS, SDLK_KP_MINUS):
                    fps = max(1.0, fps - 1.0)
            elif event.type == SDL_MOUSEBUTTONDOWN:
                mx, my = event.x, CANVAS_HEIGHT - event.y
                left = SHEET_X - sheet_width / 2
                top = SHEET_Y + sheet_height / 2
                if left <= mx < left + sheet_width and top - sheet_height <= my <= top:
                    selected_frame = min(
                        COLUMNS - 1,
                        int((mx - left) / (sheet_width / COLUMNS)),
                    )
                    accumulator = 0.0

        if playing:
            accumulator += dt
            frame_duration = 1.0 / fps
            while accumulator >= frame_duration:
                selected_frame = (selected_frame + 1) % COLUMNS
                accumulator -= frame_duration

        clear_canvas()

        # Sheet overview.
        sheet.draw(SHEET_X, SHEET_Y, sheet_width, sheet_height)
        if show_grid:
            left = SHEET_X - sheet_width / 2
            top = SHEET_Y + sheet_height / 2
            for col in range(COLUMNS + 1):
                x = left + col * sheet_width / COLUMNS
                draw_line(x, top - sheet_height, x, top, 100, 120, 145)
            for row in range(ROWS + 1):
                y = top - row * sheet_height / ROWS
                draw_line(left, y, left + sheet_width, y, 100, 120, 145)

        selected_left = round(selected_frame * sheet.w / COLUMNS)
        selected_right = round((selected_frame + 1) * sheet.w / COLUMNS)
        selected_width = selected_right - selected_left
        selected_x = (
            SHEET_X - sheet_width / 2
            + (selected_left + selected_width / 2) * SHEET_SCALE
        )
        selected_y = SHEET_Y
        draw_rectangle(
            selected_x - selected_width * SHEET_SCALE / 2,
            selected_y - sheet_height / 2,
            selected_x + selected_width * SHEET_SCALE / 2,
            selected_y + sheet_height / 2,
            255, 75, 75,
        )

        # Enlarged current frame, using the same cell coordinates as the sheet.
        sheet.clip_draw(
            selected_left,
            0,
            selected_width,
            sheet.h,
            PREVIEW_X,
            PREVIEW_Y,
            preview_width,
            preview_height,
        )
        draw_rectangle(
            PREVIEW_X - preview_width / 2,
            PREVIEW_Y - preview_height / 2,
            PREVIEW_X + preview_width / 2,
            PREVIEW_Y + preview_height / 2,
            80, 90, 110,
        )

        draw_label(font, 'mc_run.png  |  Animation Viewer', 35, 715)
        draw_label(
            font,
            'Sprite sheet: {} horizontal frames, {} x {} px'.format(
                COLUMNS, sheet.w, sheet.h
            ),
            35,
            680,
        )
        draw_label(font, 'Click a frame to select   |   Left/Right: frame   |   Space: play/pause', 35, 640)
        draw_label(font, 'G: grid   |   +/-: speed   |   Esc: quit', 35, 612)
        draw_label(font, 'Run animation', 850, 690)
        draw_label(font, 'Frame: {}/{}     Speed: {:.0f} fps     {}'.format(
            selected_frame + 1, COLUMNS, fps, 'Playing' if playing else 'Paused'), 850, 660)
        update_canvas()
        delay(0.01)

    close_canvas()


if __name__ == '__main__':
    main()
