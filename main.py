import time

from pico2d import *

import game_world
import main_character
from action_recorder import ActionRecorder
from camera import Camera
from echo_character import EchoCharacter
from echo_slot_ui import draw_echo_slot_ui, load_echo_slot_font
from hold_action_effect import draw_hold_action_effect
from hold_key_tracker import HoldKeyTracker
from recording_effect import draw_recording_effect
from stage_background import StageBackground
from stage_map import StageMap
from stage_progress import next_stage, stage_path
from title_screen import TitleScreen

player = None
level_map = None
stage_background = None
FIXED_DT = 1 / 60
HOLD_DURATION_SECONDS = 2.0
action_recorder = ActionRecorder(fixed_dt=FIXED_DT)
active_echo = None
pending_player_restore = None
saved_player_position = None
hotkey_keys_down = set()
hold_key_tracker = HoldKeyTracker(HOLD_DURATION_SECONDS)
hold_action_effect = None
HOLD_EFFECT_DURATION = 0.65
camera = Camera(1280, 720, zoom=1.0)
echo_slot_font = None
world_number = 1
stage_number = 1
game_complete = False
screen = 'game'
title_screen = None


def stop_recording():
    global pending_player_restore

    start_pose = action_recorder.stop()
    if start_pose is not None:
        pending_player_restore = start_pose


def handle_events():
    global running, active_echo, pending_player_restore, saved_player_position
    global hold_action_effect, screen, world_number, stage_number, game_complete

    event_list = get_events()
    for key in hold_key_tracker.ready_keys(time.perf_counter()) if screen == 'game' else ():
        if key == SDLK_c and player is not None:
            saved_player_position = player.capture_position()
            hold_action_effect = ('save', time.perf_counter())
        elif (
            key == SDLK_z
            and player is not None
            and saved_player_position is not None
        ):
            player.restore_position(saved_player_position)
            pending_player_restore = None
            hold_action_effect = ('restore', time.perf_counter())

    for event in event_list:
        if event.type == SDL_QUIT:
            running = False
        elif screen == 'title':
            action = title_screen.handle_event(event)
            if action == 'start':
                world_number, stage_number = 1, 1
                game_complete = False
                reset_world()
                screen = 'game'
            elif action == 'quit':
                running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_r:
            reset_world()
        elif event.type == SDL_KEYDOWN and event.key in (SDLK_c, SDLK_z):
            hold_key_tracker.key_down(event.key, time.perf_counter())
        elif event.type == SDL_KEYUP and event.key in (SDLK_c, SDLK_z):
            hold_key_tracker.key_up(event.key)
        elif event.type == SDL_KEYDOWN and event.key == SDLK_e:
            if event.key not in hotkey_keys_down:
                hotkey_keys_down.add(event.key)
                if level_map is not None and player is not None:
                    level_map.collect_echo_device(player)
        elif event.type == SDL_KEYDOWN and event.key in (SDLK_i, SDLK_j):
            if event.key not in hotkey_keys_down:
                hotkey_keys_down.add(event.key)
                if level_map is None or not level_map.echo_unlocked:
                    continue
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
                        fixed_dt=FIXED_DT,
                    )
                    game_world.add_object(active_echo, 3)
        elif event.type == SDL_KEYUP and event.key in hotkey_keys_down:
            hotkey_keys_down.discard(event.key)
        else:
            if player is not None:
                player.handle_event(event)



def reset_world():
    global player, level_map, stage_background, active_echo, pending_player_restore
    global saved_player_position, hold_action_effect

    game_world.world = [[] for _ in range(6)]
    level_map = StageMap(stage_path(world_number, stage_number))
    stage_background = StageBackground(
        level_map.pixel_width,
        level_map.pixel_height,
        level_map.background_path,
    )
    game_world.add_object(stage_background, 0)
    game_world.add_object(level_map, 1)

    action_recorder.reset()
    active_echo = None
    pending_player_restore = None
    saved_player_position = None
    hold_action_effect = None
    hold_key_tracker.reset()
    hotkey_keys_down.clear()

    spawn_x, spawn_y = level_map.player_spawn or (400.0, 64.0)
    player = main_character.MainCharacter(
        x=spawn_x,
        y=spawn_y,
        collision_map=level_map,
    )
    game_world.add_object(player, 3)


def update_world(dt):
    global active_echo, pending_player_restore
    global world_number, stage_number, game_complete

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

    if level_map is not None and player is not None:
        actors = [player]
        if active_echo is not None:
            actors.append(active_echo)
        level_map.update_mechanisms(actors)

    if player is not None and level_map is not None:
        camera.follow(
            player.x,
            player.y + player.DRAW_SIZE * (
                0.5 - player.FRAME_FOOT_OFFSET / player.FRAME_HEIGHT
            ),
            level_map.pixel_width,
            level_map.pixel_height,
        )
        for stage_exit in level_map.stage_exits:
            left, bottom, right, top = stage_exit.rect
            al, ab, ar, at = player.get_collision_box()
            if ar <= left or al >= right or at <= bottom or ab >= top:
                continue
            following = next_stage(world_number, stage_number)
            if following is None:
                game_complete = True
            elif stage_path(*following).is_file():
                world_number, stage_number = following
                reset_world()
            break

def render_world():
    global hold_action_effect

    clear_canvas()
    if screen == 'title':
        title_screen.draw()
        update_canvas()
        return
    game_world.render(camera)
    if action_recorder.is_recording:
        draw_recording_effect(camera.width, camera.height)
    if hold_action_effect is not None:
        action, started_at = hold_action_effect
        elapsed = time.perf_counter() - started_at
        if elapsed < HOLD_EFFECT_DURATION:
            draw_hold_action_effect(
                camera.width,
                camera.height,
                action,
                elapsed,
            )
        else:
            hold_action_effect = None
    if level_map is not None and player is not None:
        level_map.draw_interaction_ui(player, echo_slot_font, camera)
        if level_map.echo_unlocked:
            draw_echo_slot_ui(action_recorder, active_echo, echo_slot_font)
    update_canvas()

def main():
    global running, echo_slot_font, screen, title_screen
    running = True
    open_canvas(1280, 720)
    echo_slot_font = load_echo_slot_font()
    title_screen = TitleScreen()
    screen = 'title'
    last_frame_time = time.perf_counter()
    accumulator = 0.0
    while running:
        handle_events()
        now = time.perf_counter()
        accumulator = min(accumulator + min(now - last_frame_time, 0.1), 0.1)
        last_frame_time = now
        while screen == 'game' and accumulator >= FIXED_DT:
            update_world(FIXED_DT)
            accumulator -= FIXED_DT
        if screen == 'title':
            accumulator = 0.0
        render_world()
        delay(0.01)
    close_canvas()


if __name__ == '__main__':
    main()
