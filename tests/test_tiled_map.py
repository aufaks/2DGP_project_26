import unittest
from pathlib import Path
from unittest.mock import patch

from main_character import MainCharacter
from tiled_map import TiledMap


class FakeImage:
    w = 128
    h = 32

    def clip_composite_draw(self, *args):
        pass


class TiledMapTests(unittest.TestCase):
    def setUp(self):
        project_root = Path(__file__).resolve().parents[1]
        self.map_path = project_root / 'maps' / 'stage_01.tmj'
        self.load_image = patch('tiled_map.load_image', return_value=FakeImage())
        self.load_image.start()
        self.addCleanup(self.load_image.stop)

    def test_loads_starter_map_tiles_collision_and_spawn(self):
        tiled_map = TiledMap(self.map_path)

        self.assertEqual((tiled_map.width, tiled_map.height), (25, 18))
        self.assertEqual(len(tiled_map.tile_layers), 2)
        self.assertEqual(tiled_map.collision_rects, [(0, 0, 800, 64)])
        self.assertEqual(tiled_map.player_spawn, (96, 64))

    def test_resolves_ground_collision_and_wall_collision(self):
        tiled_map = TiledMap(self.map_path)

        x, y, grounded, hit_ceiling = tiled_map.move_actor(
            96, 64, 36, 60, 0, -20
        )
        self.assertEqual((x, y), (96, 64))
        self.assertTrue(grounded)
        self.assertFalse(hit_ceiling)

        tiled_map.collision_rects.append((128, 0, 160, 200))
        x, _, _, _ = tiled_map.move_actor(96, 64, 36, 60, 50, 0)
        self.assertEqual(x, 110)

    def test_draws_tiles_in_layer_order(self):
        tiled_map = TiledMap(self.map_path)
        image = tiled_map.tilesets[0]['image_object']
        draw_count = 0

        def count_draws(*args):
            nonlocal draw_count
            draw_count += 1

        image.clip_composite_draw = count_draws
        tiled_map.draw()

        self.assertEqual(draw_count, 500)

    def test_player_uses_tiled_spawn_and_lands_on_tiled_collision(self):
        tiled_map = TiledMap(self.map_path)
        with patch('main_character.load_image', return_value=FakeImage()):
            player = MainCharacter(
                x=tiled_map.player_spawn[0],
                y=tiled_map.player_spawn[1],
                collision_map=tiled_map,
            )

        self.assertTrue(player.grounded)
        player.grounded = False
        player.velocity_y = player.JUMP_SPEED
        for _ in range(120):
            player.update(1 / 60)

        self.assertTrue(player.grounded)
        self.assertEqual(player.y, 64)


if __name__ == '__main__':
    unittest.main()
