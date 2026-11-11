"""Sprite sheet animation viewer for the character's movement animations.

Run with: python animation_viewer.py

Click a frame in the sheet to select it. Use Left/Right to step frames,
1-4 to select an animation, Space to pause, +/- to adjust playback speed,
and G to toggle the grid.
"""

import os
import time

from pico2d import *


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUN_SPRITE_PATH = os.path.join(BASE_DIR, 'sprite', 'mc_run.png')
JUMP_SPRITE_PATH = os.path.join(BASE_DIR, 'sprite', 'mc_jump_fall_land.png')

ANIMATIONS = {
    'Run': {'sheet': 'run', 'start': 0, 'count': 8, 'loop': True},
    'Jump': {'sheet': 'jump', 'start': 0, 'count': 4, 'loop': False},
    'Fall': {'sheet': 'jump', 'start': 4, 'count': 3, 'loop': True},
    'Land': {'sheet': 'jump', 'start': 7, 'count': 3, 'loop': False},
}
SHEET_FRAME_COUNTS = {'run': 8, 'jump': 10}
ANIMATION_KEYS = {
    SDLK_1: 'Run',
    SDLK_2: 'Jump',
    SDLK_3: 'Fall',
    SDLK_4: 'Land',
}
ROWS = 1
FPS = 8.0

CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 760
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
    sheets = {
        'run': load_image(RUN_SPRITE_PATH),
        'jump': load_image(JUMP_SPRITE_PATH),
    }
    preview_width = PREVIEW_SIZE
    font_path = os.path.join(BASE_DIR, 'ENfont.ttf')
    if not os.path.exists(font_path):
        font_path = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf')
    font = load_font(font_path, 18)

    selected_animation = 'Run'
    selected_frame = 0
    playing = True
    finished = False
    show_grid = True
    fps = FPS
    accumulator = 0.0
    last_time = time.perf_counter()
    running = True

    def select_animation(name):
        nonlocal selected_animation, selected_frame, accumulator, finished, playing
        selected_animation = name
        selected_frame = ANIMATIONS[name]['start']
        accumulator = 0.0
        finished = False
        playing = True

    while running:
        now = time.perf_counter()
        dt = min(now - last_time, 0.1)
        last_time = now

        animation = ANIMATIONS[selected_animation]
        sheet = sheets[animation['sheet']]
        frame_count = SHEET_FRAME_COUNTS[animation['sheet']]
        frame_width = sheet.w / frame_count
        sheet_scale = min(0.38, 790 / sheet.w)
        sheet_width = sheet.w * sheet_scale
        sheet_height = sheet.h * sheet_scale
        preview_height = PREVIEW_SIZE * sheet.h / frame_width

        for event in get_events():
            animation = ANIMATIONS[selected_animation]
            if event.type == SDL_QUIT:
                running = False
            elif event.type == SDL_KEYDOWN:
                if event.key == SDLK_ESCAPE:
                    running = False
                elif event.key == SDLK_SPACE:
                    if finished:
                        select_animation(selected_animation)
                    else:
                        playing = not playing
                elif event.key == SDLK_g:
                    show_grid = not show_grid
                elif event.key in ANIMATION_KEYS:
                    select_animation(ANIMATION_KEYS[event.key])
                elif event.key in (SDLK_LEFT, SDLK_a):
                    selected_frame = animation['start'] + (
                        selected_frame - animation['start'] - 1
                    ) % animation['count']
                    accumulator = 0.0
                    finished = False
                elif event.key in (SDLK_RIGHT, SDLK_d):
                    selected_frame = animation['start'] + (
                        selected_frame - animation['start'] + 1
                    ) % animation['count']
                    accumulator = 0.0
                    finished = False
                elif event.key in (SDLK_EQUALS, SDLK_PLUS, SDLK_KP_PLUS):
                    fps = min(30.0, fps + 1.0)
                elif event.key in (SDLK_MINUS, SDLK_KP_MINUS):
                    fps = max(1.0, fps - 1.0)
            elif event.type == SDL_MOUSEBUTTONDOWN:
                mx, my = event.x, CANVAS_HEIGHT - event.y
                left = SHEET_X - sheet_width / 2
                top = SHEET_Y + sheet_height / 2
                if left <= mx < left + sheet_width and top - sheet_height <= my <= top:
                    clicked_frame = min(
                        frame_count - 1,
                        int((mx - left) / (sheet_width / frame_count)),
                    )
                    for name, clip in ANIMATIONS.items():
                        if (
                            clip['sheet'] == animation['sheet']
                            and clip['start'] <= clicked_frame
                            < clip['start'] + clip['count']
                        ):
                            selected_animation = name
                            animation = clip
                            break
                    selected_frame = clicked_frame
                    accumulator = 0.0
                    finished = False

        animation = ANIMATIONS[selected_animation]
        sheet = sheets[animation['sheet']]
        frame_count = SHEET_FRAME_COUNTS[animation['sheet']]
        if playing:
            accumulator += dt
            frame_duration = 1.0 / fps
            while accumulator >= frame_duration:
                last_frame = animation['start'] + animation['count'] - 1
                if animation['loop']:
                    selected_frame = (
                        animation['start']
                        + (selected_frame - animation['start'] + 1)
                        % animation['count']
                    )
                elif selected_frame < last_frame:
                    selected_frame += 1
                    if selected_frame == last_frame:
                        playing = False
                        finished = True
                else:
                    playing = False
                    finished = True
                accumulator -= frame_duration

        clear_canvas()

        # Sheet overview.
        sheet.draw(SHEET_X, SHEET_Y, sheet_width, sheet_height)
        if show_grid:
            left = SHEET_X - sheet_width / 2
            top = SHEET_Y + sheet_height / 2
            for col in range(frame_count + 1):
                x = left + col * sheet_width / frame_count
                draw_line(x, top - sheet_height, x, top, 100, 120, 145)
            for row in range(ROWS + 1):
                y = top - row * sheet_height / ROWS
                draw_line(left, y, left + sheet_width, y, 100, 120, 145)

        selected_left = round(selected_frame * sheet.w / frame_count)
        selected_right = round((selected_frame + 1) * sheet.w / frame_count)
        selected_width = selected_right - selected_left
        selected_x = (
            SHEET_X - sheet_width / 2
            + (selected_left + selected_width / 2) * sheet_scale
        )
        selected_y = SHEET_Y
        draw_rectangle(
            selected_x - selected_width * sheet_scale / 2,
            selected_y - sheet_height / 2,
            selected_x + selected_width * sheet_scale / 2,
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

        draw_label(
            font,
            '{}  |  Animation Viewer'.format(os.path.basename(
                RUN_SPRITE_PATH if animation['sheet'] == 'run'
                else JUMP_SPRITE_PATH
            )),
            35,
            715,
        )
        draw_label(
            font,
            'Sprite sheet: {} horizontal frames, {} x {} px'.format(
                frame_count, sheet.w, sheet.h
            ),
            35,
            680,
        )
        draw_label(
            font,
            '1: Run   2: Jump   3: Fall   4: Land   |   Click: select frame',
            35,
            640,
        )
        draw_label(
            font,
            'Left/Right: frame   |   Space: play/pause   |   G: grid   |   Esc: quit',
            35,
            612,
        )
        draw_label(font, '{} animation'.format(selected_animation), 850, 690)
        status = 'Finished' if finished else 'Playing' if playing else 'Paused'
        draw_label(
            font,
            'Frame: {}/{}     Speed: {:.0f} fps     {}'.format(
                selected_frame - animation['start'] + 1,
                animation['count'],
                fps,
                status,
            ),
            850,
            660,
        )
        update_canvas()
        delay(0.01)

    close_canvas()


if __name__ == '__main__':
    main()
