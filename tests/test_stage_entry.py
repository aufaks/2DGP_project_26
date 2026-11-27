import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from main_character import MainCharacter


class StageEntryTests(unittest.TestCase):
    def test_player_walks_to_spawn_then_stops(self):
        image = object()
        player = MainCharacter(
            x=-50,
            y=100,
            collision_map=SimpleNamespace(
                character_scale=1.0,
                is_supported=lambda *args: True,
            ),
            sprite_images=(image, image, image),
        )

        finished = player.walk_in(1.0, 100.0)

        self.assertTrue(finished)
        self.assertEqual(player.x, 100.0)
        self.assertFalse(player.is_moving)
        self.assertEqual(player.state, 'IDLE')

    def test_entry_update_ends_in_gameplay_at_spawn(self):
        player = SimpleNamespace(walk_in=Mock(return_value=True))
        stage = SimpleNamespace(update=Mock())
        with patch.object(main, 'screen', 'stage_entry'), \
                patch.object(main, 'player', player), \
                patch.object(main, 'level_map', stage), \
                patch.object(main, 'stage_entry_target_x', 100.0):
            main.update_world(1 / 60)

            self.assertEqual(main.screen, 'game')
            player.walk_in.assert_called_once_with(1 / 60, 100.0)
            stage.update.assert_called_once_with(1 / 60)


if __name__ == '__main__':
    unittest.main()
