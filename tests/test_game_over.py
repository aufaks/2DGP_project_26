import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import game_world
import main


class GameOverTests(unittest.TestCase):
    def test_player_below_map_enters_game_over(self):
        player = SimpleNamespace(
            sprite_top=lambda: -1,
            pressed_keys={1},
            _pending_command=object(),
            _jump_pressed=True,
        )
        stage = SimpleNamespace()
        with patch.object(main, 'player', player), \
                patch.object(main, 'level_map', stage), \
                patch.object(main, 'active_echo', None), \
                patch.object(main, 'recording_echo', None), \
                patch.object(main, 'screen', 'game'), \
                patch.object(main, 'game_over_elapsed', 0.0), \
                patch.object(main, 'stop_recording') as stop_recording, \
                patch.object(game_world, 'update'):
            main.update_world(1 / 60)

            self.assertEqual(main.screen, 'game_over')
            self.assertEqual(main.game_over_elapsed, 0.0)
            self.assertFalse(player.pressed_keys)
            self.assertIsNone(player._pending_command)
            self.assertFalse(player._jump_pressed)
            stop_recording.assert_called_once_with()

    def test_character_visible_below_collision_box_does_not_trigger_game_over(self):
        player = SimpleNamespace(sprite_top=lambda: 5, x=100, y=-70,
                                 DRAW_SIZE=96, FRAME_FOOT_OFFSET=24,
                                 FRAME_HEIGHT=254, get_collision_box=lambda: (82, -70, 118, -10))
        stage = SimpleNamespace(pixel_width=1280, pixel_height=720,
                                stage_exits=(), update_mechanisms=Mock())
        with patch.object(main, 'player', player), \
                patch.object(main, 'level_map', stage), \
                patch.object(main, 'active_echo', None), \
                patch.object(main, 'recording_echo', None), \
                patch.object(main, 'screen', 'game'), \
                patch.object(game_world, 'update'):
            main.update_world(1 / 60)
            self.assertEqual(main.screen, 'game')

    def test_game_over_waits_then_restarts_current_stage(self):
        with patch.object(main, 'screen', 'game_over'), \
                patch.object(
                    main,
                    'game_over_elapsed',
                    main.GAME_OVER_DURATION - 0.01,
                ), \
                patch.object(main, 'reset_world') as reset_world:
            main.update_world(0.02)

            reset_world.assert_called_once_with(keep_recording=True)
            self.assertEqual(main.screen, 'stage_entry')
            self.assertEqual(main.game_over_elapsed, 0.0)

    def test_game_over_effect_is_rendered(self):
        effect = SimpleNamespace(draw=Mock(), shake_offset=Mock(return_value=(3, -2)))
        with patch.object(main, 'screen', 'game_over'), \
                patch.object(main, 'game_over_effect', effect), \
                patch.object(main, 'clear_game_canvas'), \
                patch.object(main, 'update_canvas'), \
                patch.object(game_world, 'render') as render:
            main.render_world()

            render_camera = render.call_args.args[0]
            self.assertEqual(render_camera.world_to_screen(640, 360),
                             (643, 358))
            effect.draw.assert_called_once_with(
                main.camera.width,
                main.camera.height,
                main.game_over_elapsed,
                main.screen_edge_effect,
            )


if __name__ == '__main__':
    unittest.main()
