import os
import time

from pico2d import *

import game_world
import main_character
from camera import Camera
from tiled_map import TiledMap

player = None
level_map = None
camera = Camera(800, 576, zoom=0.75)


def handle_events():
    global running

    event_list = get_events()
    for event in event_list:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
        else:
            if player is not None:
                player.handle_event(event)



def reset_world():
    global player, level_map

    map_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'maps',
        'stage_01.tmj',
    )
    level_map = TiledMap(map_path)
    game_world.add_object(level_map, 0)

    spawn_x, spawn_y = level_map.player_spawn or (400.0, 64.0)
    player = main_character.MainCharacter(
        x=spawn_x,
        y=spawn_y,
        collision_map=level_map,
    )
    game_world.add_object(player, 3)


def update_world(dt):
    game_world.update(dt)
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
    update_canvas()

running = True
open_canvas(800, 576)
reset_world()
last_frame_time = time.perf_counter()
while running:
    handle_events()
    now = time.perf_counter()
    dt = min(now - last_frame_time, 0.1)
    last_frame_time = now
    update_world(dt)
    render_world()
    delay(0.01)
close_canvas()
