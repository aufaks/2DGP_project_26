import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDLK_i, SDLK_j, SDLK_RIGHT

import game_world
import main
from action_recorder import ActionRecorder
from main_character import MainCharacter


class FlatMap:
    echo_unlocked = True
    pixel_width = 1280
    pixel_height = 720
    stage_exits = ()

    def is_supported(self, *args):
        return True

    def move_actor(self, x, y, width, height, dx, dy):
        return x + dx, y, True, False

    def update_mechanisms(self, actors):
        self.actors = tuple(actors)


class RecordingControlTests(unittest.TestCase):
    def test_body_stays_put_while_echo_records_then_replays(self):
        image = SimpleNamespace()
        sprites = (image, image, image)
        stage = FlatMap()
        player = MainCharacter(x=200, y=136, collision_map=stage,
                               sprite_images=sprites)
        recorder = ActionRecorder(max_duration_seconds=3 / 60, fixed_dt=1 / 60)
        layers = [[] for _ in range(6)]
        layers[3].append(player)

        with patch.object(main, 'player', player), \
                patch.object(main, 'level_map', stage), \
                patch.object(main, 'action_recorder', recorder), \
                patch.object(main, 'active_echo', None), \
                patch.object(main, 'recording_echo', None), \
                patch.object(main, 'screen', 'game'), \
                patch.object(game_world, 'world', layers), \
                patch.object(main, 'get_events') as events:
            main.hotkey_keys_down.clear()
            main.hold_key_tracker.reset()
            self.addCleanup(main.hotkey_keys_down.clear)
            events.return_value = [SimpleNamespace(type=SDL_KEYDOWN, key=SDLK_i)]
            main.handle_events()
            self.assertTrue(player.frozen)
            self.assertIn(main.recording_echo, layers[3])
            self.assertEqual(main.recording_echo.palette_index, 0)
            self.assertEqual(main.recording_echo.x, player.x)

            events.return_value = [SimpleNamespace(type=SDL_KEYDOWN, key=SDLK_RIGHT)]
            main.handle_events()
            for _ in range(2):
                main.update_world(1 / 60)
            self.assertEqual(player.x, 200)
            self.assertGreater(main.recording_echo.x, 200)
            self.assertIn(main.recording_echo, stage.actors)

            main.update_world(1 / 60)  # recording automatically ends
            self.assertIsNone(main.recording_echo)
            self.assertFalse(player.frozen)
            self.assertEqual(player.x, 200)
            self.assertEqual(len(recorder.frames), 3)
            self.assertTrue(all(frame.move_x == 1 for frame in recorder.frames))

            events.return_value = [
                SimpleNamespace(type=SDL_KEYUP, key=SDLK_i),
                SimpleNamespace(type=SDL_KEYUP, key=SDLK_RIGHT),
                SimpleNamespace(type=SDL_KEYDOWN, key=SDLK_j),
            ]
            main.handle_events()
            self.assertIsNotNone(main.active_echo)
            main.update_world(1 / 60)
            self.assertGreater(main.active_echo.x, 200)
            self.assertEqual(player.x, 200)


if __name__ == '__main__':
    unittest.main()
