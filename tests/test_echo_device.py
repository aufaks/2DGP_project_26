import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main
from action_recorder import ActionRecorder
from camera import Camera
from main_character import MainCharacter
from tiled_map import TiledMap


class EchoDeviceTests(unittest.TestCase):
    def setUp(self):
        with patch('tiled_map.load_image', return_value=SimpleNamespace(w=192, h=64)):
            self.level = TiledMap(Path(__file__).resolve().parents[1] / 'maps/stage_01.tmj')
        self.player = MainCharacter(x=376, y=160, collision_map=self.level,
                                    sprite_images=(None, None, None))
        self.recorder = ActionRecorder()
        for name, value in [('level_map', self.level), ('player', self.player),
                            ('action_recorder', self.recorder), ('active_echo', None),
                            ('hotkey_keys_down', set())]:
            patcher = patch.object(main, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def event(self, key, event_type=main.SDL_KEYDOWN):
        with patch.object(main, 'get_events', return_value=[
            SimpleNamespace(type=event_type, key=key)
        ]):
            main.handle_events()

    def test_record_and_playback_blocked_until_e_pickup(self):
        self.assertFalse(self.level.echo_unlocked)
        self.event(main.SDLK_i)
        self.assertFalse(self.recorder.is_recording)
        self.event(main.SDLK_j)
        self.assertIsNone(main.active_echo)
        self.event(main.SDLK_i, main.SDL_KEYUP)
        self.event(main.SDLK_j, main.SDL_KEYUP)
        self.event(main.SDLK_e)
        self.assertTrue(self.level.echo_unlocked)
        self.assertTrue(self.level.echo_devices[0].collected)
        self.event(main.SDLK_i)
        self.assertTrue(self.recorder.is_recording)
        main.update_world(1 / 60)
        self.event(main.SDLK_i, main.SDL_KEYUP)
        self.event(main.SDLK_i)
        self.assertTrue(self.recorder.has_recording)
        self.event(main.SDLK_j)
        self.assertIsNotNone(main.active_echo)
        self.addCleanup(main.game_world.remove_object, main.active_echo)

    def test_remote_or_repeated_pickup_does_not_unlock_or_respawn(self):
        self.player.x = 1200
        self.event(main.SDLK_e)
        self.assertFalse(self.level.echo_unlocked)
        self.player.x = 376
        self.event(main.SDLK_e)  # Held key must not auto-collect on arrival.
        self.assertFalse(self.level.echo_unlocked)
        self.event(main.SDLK_e, main.SDL_KEYUP)
        self.event(main.SDLK_e)
        self.assertTrue(self.level.echo_unlocked)
        self.assertFalse(self.level.collect_echo_device(self.player))
        self.player.restore_position((96, 160))
        self.assertTrue(self.level.echo_unlocked)

    def test_pickup_is_non_solid_and_ui_hides_after_collection(self):
        device = self.level.echo_devices[0]
        self.assertNotIn(device.rect, self.level.solid_rects)
        font = SimpleNamespace(draw=unittest.mock.Mock())
        self.level.draw_interaction_ui(self.player, font, Camera(1280, 720))
        self.assertIn('[E]', font.draw.call_args.args[2])
        self.level.collect_echo_device(self.player)
        with patch('game_objects.draw_rectangle') as draw:
            device.draw()
        draw.assert_not_called()

    def test_slot_ui_hidden_until_unlock(self):
        with patch.object(main, 'clear_canvas'), patch.object(main, 'update_canvas'), \
                patch.object(main.game_world, 'render'), \
                patch.object(main, 'hold_action_effect', None), \
                patch.object(main, 'echo_slot_font', SimpleNamespace(draw=lambda *args: None)), \
                patch.object(main, 'draw_echo_slot_ui') as draw:
            main.render_world()
            draw.assert_not_called()
            self.level.collect_echo_device(self.player)
            main.render_world()
            draw.assert_called_once()


if __name__ == '__main__':
    unittest.main()
