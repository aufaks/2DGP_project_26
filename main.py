import time

import pico2d
from pico2d import *

import game_world
import main_character
from action_recorder import ActionRecorder
from camera import Camera
from echo_character import EchoCharacter
from echo_slot_ui import draw_echo_slot_ui, load_echo_slot_font
from hold_action_effect import draw_hold_action_effect
from hold_key_tracker import HoldKeyTracker
from pause_menu import PauseMenu
from recording_effect import draw_recording_effect
from stage_background import StageBackground
from stage_map import StageMap
from stage_progress import next_stage, stage_path
from stage_select import StageSelect
from title_screen import TitleScreen

player = None
level_map = None
stage_background = None
FIXED_DT = 1 / 60
HOLD_DURATION_SECONDS = 2.0
action_recorder = ActionRecorder(fixed_dt=FIXED_DT)
active_echo = None
recording_echo = None
saved_player_position = None
saved_echo_position = None
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
stage_select = None
pause_menu = None


def maximize_game_window():
    SDL_SetWindowResizable(pico2d.window, True)
    SDL_MaximizeWindow(pico2d.window)


def stop_recording():
    global recording_echo, saved_echo_position

    action_recorder.stop()
    if recording_echo is not None:
        if player is not None:
            player.pressed_keys.update(recording_echo.pressed_keys)
            player.frozen = False
            player._pending_command = None
            player._jump_pressed = False
        game_world.remove_object(recording_echo)
        recording_echo = None
    saved_echo_position = None


def start_recording():
    global recording_echo, saved_echo_position

    action_recorder.start(player)
    saved_echo_position = None
    recording_echo = EchoCharacter(
        action_recorder.start_pose,
        (),
        level_map,
        player.sprite_images,
        fixed_dt=FIXED_DT,
        palette_index=0,
        recording=True,
    )
    recording_echo.pressed_keys.update(player.pressed_keys)
    player.pressed_keys.clear()
    player._pending_command = None
    player._jump_pressed = False
    game_world.add_object(recording_echo, 3)


def pause_game():
    global screen

    for actor in (player, active_echo, recording_echo):
        if actor is not None:
            actor.pressed_keys.clear()
            actor._pending_command = None
            actor._jump_pressed = False
    hold_key_tracker.reset()
    hotkey_keys_down.clear()
    pause_menu.selected = 0
    screen = 'pause'


def handle_events():
    global running, active_echo, saved_player_position, saved_echo_position
    global hold_action_effect, screen, world_number, stage_number, game_complete

    event_list = get_events()
    for key in hold_key_tracker.ready_keys(time.perf_counter()) if screen == 'game' else ():
        controlled_actor = recording_echo or player
        if key == SDLK_c and controlled_actor is not None:
            if recording_echo is not None:
                saved_echo_position = controlled_actor.capture_position()
            else:
                saved_player_position = controlled_actor.capture_position()
            hold_action_effect = ('save', time.perf_counter())
        elif (
            key == SDLK_z
            and controlled_actor is not None
        ):
            saved_position = (saved_echo_position if recording_echo is not None
                              else saved_player_position)
            if saved_position is not None:
                controlled_actor.restore_position(saved_position)
                hold_action_effect = ('restore', time.perf_counter())

    for event in event_list:
        if event.type == SDL_QUIT:
            running = False
        elif screen == 'title':
            action = title_screen.handle_event(event)
            if action == 'start':
                stage_select.show_worlds()
                screen = 'select'
            elif action == 'quit':
                running = False
        elif screen == 'select':
            action = stage_select.handle_event(event)
            if action is not None:
                if action[0] == 'title':
                    screen = 'title'
                elif action[0] == 'play':
                    world_number, stage_number = action[1:]
                    game_complete = False
                    reset_world()
                    screen = 'game'
        elif screen == 'pause':
            action = pause_menu.handle_event(event)
            if action == 'continue':
                screen = 'game'
            elif action == 'restart':
                reset_world()
                screen = 'game'
            elif action == 'title':
                screen = 'title'
        elif (
            screen == 'game'
            and event.type == SDL_KEYDOWN
            and event.key == SDLK_ESCAPE
        ):
            pause_game()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            stage_select.show_stages(world_number)
            stage_select.stage = stage_number
            screen = 'select'
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
                        start_recording()
                elif event.key == SDLK_j and recording_echo is None and \
                        active_echo is None and \
                        action_recorder.has_recording:
                    active_echo = EchoCharacter(
                        action_recorder.start_pose,
                        action_recorder.frames,
                        level_map,
                        player.sprite_images,
                        fixed_dt=FIXED_DT,
                        palette_index=0,
                    )
                    game_world.add_object(active_echo, 3)
        elif event.type == SDL_KEYUP and event.key in hotkey_keys_down:
            hotkey_keys_down.discard(event.key)
        else:
            controlled_actor = recording_echo or player
            if controlled_actor is not None:
                controlled_actor.handle_event(event)



def reset_world():
    global player, level_map, stage_background, active_echo, recording_echo
    global saved_player_position, saved_echo_position, hold_action_effect

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
    recording_echo = None
    saved_player_position = None
    saved_echo_position = None
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
    global active_echo
    global world_number, stage_number, game_complete, screen

    if screen != 'game':
        return

    recording_finished = False
    if recording_echo is not None:
        command = recording_echo.command_for_tick()
        recording_finished = action_recorder.record(command)

    game_world.update(dt)
    if recording_finished:
        stop_recording()

    if active_echo is not None and active_echo.finished:
        game_world.remove_object(active_echo)
        active_echo = None

    if level_map is not None and player is not None:
        actors = [player]
        if active_echo is not None:
            actors.append(active_echo)
        if recording_echo is not None:
            actors.append(recording_echo)
        level_map.update_mechanisms(actors)

    if player is not None and level_map is not None:
        camera_target = recording_echo or player
        camera.follow(
            camera_target.x,
            camera_target.y + camera_target.DRAW_SIZE * (
                0.5 - camera_target.FRAME_FOOT_OFFSET / camera_target.FRAME_HEIGHT
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
                stage_select.show_stages(world_number)
                screen = 'select'
            elif stage_path(*following).is_file():
                world_number, stage_number = following
                reset_world()
            else:
                stage_select.show_stages(following[0])
                screen = 'select'
            break

def render_world():
    global hold_action_effect

    clear_canvas()
    if screen == 'title':
        title_screen.draw()
        update_canvas()
        return
    if screen == 'select':
        stage_select.draw()
        update_canvas()
        return
    game_world.render(camera)
    if screen == 'pause':
        pause_menu.draw()
        update_canvas()
        return
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
    global running, echo_slot_font, screen, title_screen, stage_select
    global pause_menu
    running = True
    open_canvas(1280, 720)
    maximize_game_window()
    echo_slot_font = load_echo_slot_font()
    title_screen = TitleScreen()
    stage_select = StageSelect()
    pause_menu = PauseMenu()
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
        if screen != 'game':
            accumulator = 0.0
        render_world()
        delay(0.01)
    close_canvas()


if __name__ == '__main__':
    main()
