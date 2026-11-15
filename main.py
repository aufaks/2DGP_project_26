import os
import time

from pico2d import *

import game_world
import main_character
from action_recorder import ActionRecorder
from camera import Camera
from echo_character import EchoCharacter
from recording_effect import draw_recording_effect
from tiled_map import TiledMap

player = None
level_map = None
FIXED_DT = 1 / 60
action_recorder = ActionRecorder(fixed_dt=FIXED_DT)
active_echo = None
pending_player_restore = None
hotkey_keys_down = set()
camera = Camera(800, 576, zoom=0.75)


def stop_recording():
    global pending_player_restore

    start_pose = action_recorder.stop()
    if start_pose is not None:
        pending_player_restore = start_pose


def handle_events():
    global running, active_echo

    event_list = get_events()
    for event in event_list:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
        elif event.type == SDL_KEYDOWN and event.key in (SDLK_i, SDLK_j):
            if event.key not in hotkey_keys_down:
                hotkey_keys_down.add(event.key)
                if event.key == SDLK_i and active_echo is None:
                    if action_recorder.is_recording:
                        stop_recording()
                    elif player is not None:
                        action_recorder.start(player)
                elif event.key == SDLK_j and active_echo is None and \
                        action_recorder.has_recording:
                    active_echo = EchoCharacter(
                        action_recorder.start_pose,
                        action_recorder.frames,
                        level_map,
                        player.sprite_images,
                    )
                    game_world.add_object(active_echo, 3)
        elif event.type == SDL_KEYUP and event.key in hotkey_keys_down:
            hotkey_keys_down.discard(event.key)
        else:
            if player is not None:
                player.handle_event(event)



def reset_world():
    global player, level_map, active_echo, pending_player_restore

    map_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'maps',
        'stage_01.tmj',
    )
    level_map = TiledMap(map_path)
    game_world.add_object(level_map, 0)

    action_recorder.reset()
    active_echo = None
    pending_player_restore = None

    spawn_x, spawn_y = level_map.player_spawn or (400.0, 64.0)
    player = main_character.MainCharacter(
        x=spawn_x,
        y=spawn_y,
        collision_map=level_map,
    )
    game_world.add_object(player, 3)


def update_world(dt):
    global active_echo, pending_player_restore

    if player is not None:
        command = player.command_for_tick()
        if action_recorder.record(command):
            pending_player_restore = action_recorder.start_pose

    game_world.update(dt)
    if pending_player_restore is not None and player is not None:
        player.restore_pose(pending_player_restore)
        pending_player_restore = None

    if active_echo is not None and active_echo.finished:
        game_world.remove_object(active_echo)
        active_echo = None

    if player is not None and level_map is not None:
        camera.follow(
            player.x,
            player.y + player.DRAW_SIZE * (
                0.5 - player.FRAME_FOOT_OFFSET / player.FRAME_HEIGHT
            ),
            level_map.pixel_width,
            level_map.pixel_height,
        )

def render_world():
    clear_canvas()
    game_world.render(camera)
    if action_recorder.is_recording:
        draw_recording_effect(camera.width, camera.height)
    update_canvas()

running = True
open_canvas(800, 576)
reset_world()
last_frame_time = time.perf_counter()
accumulator = 0.0
while running:
    handle_events()
    now = time.perf_counter()
    accumulator = min(accumulator + min(now - last_frame_time, 0.1), 0.1)
    last_frame_time = now
    while accumulator >= FIXED_DT:
        update_world(FIXED_DT)
        accumulator -= FIXED_DT
    render_world()
    delay(0.01)
close_canvas()
