import unittest
from pathlib import Path
from unittest.mock import patch

import main_character
from camera import Camera
from main_character import MainCharacter
from tiled_map import TiledMap


class FakeImage:
    w = 128
    h = 32

    def clip_composite_draw(self, *args):
        pass


class FakeCharacterImage:
    w = 254 * 8
    h = 254

    def __init__(self):
        self.draw_calls = []

    def clip_composite_draw(self, *args):
        self.draw_calls.append(args)


class TiledMapTests(unittest.TestCase):
    def setUp(self):
        project_root = Path(__file__).resolve().parents[1]
        self.map_path = project_root / 'maps' / 'stage_01.tmj'
        self.load_image = patch('tiled_map.load_image', return_value=FakeImage())
        self.load_image.start()
        self.addCleanup(self.load_image.stop)

    def test_loads_starter_map_tiles_collision_and_spawn(self):
        tiled_map = TiledMap(self.map_path)

        self.assertEqual((tiled_map.width, tiled_map.height), (100, 25))
        self.assertEqual(len(tiled_map.tile_layers), 2)
        self.assertEqual(tiled_map.collision_rects, [(0, 0, 3200, 160)])
        self.assertEqual(tiled_map.player_spawn, (96, 160))

        terrain = tiled_map.tile_layers[1][1]
        self.assertEqual(
            terrain[20 * tiled_map.width:(21 * tiled_map.width)],
            [1] * 100,
        )
        self.assertEqual(
            terrain[21 * tiled_map.width:],
            [2] * (4 * 100),
        )

    def test_resolves_ground_collision_and_wall_collision(self):
        tiled_map = TiledMap(self.map_path)

        x, y, grounded, hit_ceiling = tiled_map.move_actor(
            96, 160, 36, 60, 0, -20
        )
        self.assertEqual((x, y), (96, 160))
        self.assertTrue(grounded)
        self.assertFalse(hit_ceiling)

        tiled_map.collision_rects.append((128, 120, 160, 300))
        x, _, _, _ = tiled_map.move_actor(96, 160, 36, 60, 50, 0)
        self.assertEqual(x, 110)

    def test_keeps_actor_inside_map_boundaries(self):
        tiled_map = TiledMap(self.map_path)

        x, _, _, _ = tiled_map.move_actor(18, 288, 36, 60, -100, 0)
        self.assertEqual(x, 18)
        x, _, _, _ = tiled_map.move_actor(
            tiled_map.pixel_width - 18, 288, 36, 60, 100, 0
        )
        self.assertEqual(x, tiled_map.pixel_width - 18)

        _, y, grounded, _ = tiled_map.move_actor(96, 10, 36, 60, 0, -50)
        self.assertEqual(y, 0)
        self.assertTrue(grounded)
        _, y, _, hit_ceiling = tiled_map.move_actor(
            96, tiled_map.pixel_height - 60, 36, 60, 0, 100
        )
        self.assertEqual(y, tiled_map.pixel_height - 60)
        self.assertTrue(hit_ceiling)

    def test_draws_tiles_in_layer_order(self):
        tiled_map = TiledMap(self.map_path)
        image = tiled_map.tilesets[0]['image_object']
        draw_count = 0

        def count_draws(*args):
            nonlocal draw_count
            draw_count += 1

        image.clip_composite_draw = count_draws
        tiled_map.draw()

        self.assertEqual(draw_count, 3000)

    def test_camera_scales_and_centers_map_tiles(self):
        tiled_map = TiledMap(self.map_path)
        camera = Camera(800, 576, zoom=0.75)
        image = tiled_map.tilesets[0]['image_object']
        draw_calls = []
        image.clip_composite_draw = lambda *args: draw_calls.append(args)

        tiled_map.draw()
        unscaled_draw_calls = list(draw_calls)
        draw_calls.clear()
        tiled_map.draw(camera)

        self.assertEqual(len(draw_calls), 3000)
        for original, scaled in zip(unscaled_draw_calls, draw_calls):
            self.assertEqual(
                scaled[6:8],
                camera.world_to_screen(original[6], original[7]),
            )
            self.assertEqual(scaled[-2:], (24.0, 24.0))

    def test_camera_follows_player_without_showing_outside_map(self):
        camera = Camera(800, 576, zoom=0.75)

        camera.follow(1600, 400, 3200, 800)
        self.assertEqual(camera.world_to_screen(1600, 400), (400.0, 288.0))

        camera.follow(0, 0, 3200, 800)
        left, bottom = camera.world_to_screen(0, 0)
        self.assertAlmostEqual(left, 0)
        self.assertAlmostEqual(bottom, 0)
        self.assertGreaterEqual(camera.x - camera.width / (2 * camera.zoom), 0)
        self.assertGreaterEqual(camera.y - camera.height / (2 * camera.zoom), 0)

        camera.follow(3200, 800, 3200, 800)
        right, top = camera.world_to_screen(3200, 800)
        self.assertAlmostEqual(right, camera.width)
        self.assertAlmostEqual(top, camera.height)
        self.assertLessEqual(
            camera.x + camera.width / (2 * camera.zoom),
            3200,
        )
        self.assertLessEqual(
            camera.y + camera.height / (2 * camera.zoom),
            800,
        )

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
        self.assertEqual(player.y, 160)

    def test_player_jump_is_higher_and_has_more_airtime(self):
        with patch('main_character.load_image', return_value=FakeImage()):
            player = MainCharacter(ground_y=0)

        player.grounded = False
        player.velocity_y = player.JUMP_SPEED
        jump_height = 0
        airtime = 0
        while not player.grounded:
            player.update(1 / 60)
            airtime += 1 / 60
            jump_height = max(jump_height, player.y)

        self.assertGreater(jump_height, 150)
        self.assertGreater(airtime, 0.85)

    def test_player_uses_and_animates_the_horizontal_run_sheet(self):
        image = FakeCharacterImage()
        with patch('main_character.load_image', return_value=image) as load_image:
            player = MainCharacter()

        self.assertEqual(Path(load_image.call_args.args[0]).name, 'mc_run.png')

        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 0)

        player.pressed_keys.add(main_character.SDLK_d)
        player.update(0.1)
        player.update(0.03)
        player.draw()

        source_x, source_y, source_width, source_height = image.draw_calls[-1][:4]
        self.assertEqual(
            (source_x, source_y, source_width, source_height),
            (254, 0, 254, 254),
        )
        self.assertEqual(image.draw_calls[-1][-2:], (96.0, 96.0))

    def test_camera_scales_and_centers_player(self):
        image = FakeCharacterImage()
        with patch('main_character.load_image', return_value=image):
            player = MainCharacter(x=400, y=160)
        camera = Camera(800, 576, zoom=0.75)

        player.draw(camera)

        draw_call = image.draw_calls[-1]
        self.assertEqual(draw_call[6], 400.0)
        self.assertAlmostEqual(draw_call[7], 221.197, places=3)
        self.assertEqual(draw_call[-2:], (72.0, 72.0))


if __name__ == '__main__':
    unittest.main()
