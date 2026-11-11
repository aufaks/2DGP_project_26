import unittest
from pathlib import Path
from types import SimpleNamespace
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
        self.assertEqual(tiled_map.platform_rects, [(320, 320, 640, 352)])
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

    def test_platform_tiles_block_sides_top_and_bottom(self):
        tiled_map = TiledMap(self.map_path)

        x, y, grounded, hit_ceiling = tiled_map.move_actor(
            400, 200, 36, 60, 0, 180
        )
        self.assertEqual((x, y), (400, 260))
        self.assertFalse(grounded)
        self.assertTrue(hit_ceiling)

        x, y, grounded, hit_ceiling = tiled_map.move_actor(
            400, 400, 36, 60, 0, -100
        )
        self.assertEqual((x, y), (400, 352))
        self.assertTrue(grounded)
        self.assertFalse(hit_ceiling)

        x, _, _, _ = tiled_map.move_actor(200, 330, 36, 60, 200, 0)
        self.assertEqual(x, 302)

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

        self.assertGreater(jump_height, 250)
        self.assertGreater(airtime, 0.85)

    def test_player_can_jump_onto_the_tile_platform(self):
        tiled_map = TiledMap(self.map_path)
        with patch('main_character.load_image', return_value=FakeImage()):
            player = MainCharacter(x=200, y=160, collision_map=tiled_map)

        player.handle_event(SimpleNamespace(
            type=main_character.SDL_KEYDOWN,
            key=main_character.SDLK_SPACE,
        ))
        player.handle_event(SimpleNamespace(
            type=main_character.SDL_KEYDOWN,
            key=main_character.SDLK_d,
        ))
        for _ in range(120):
            player.update(1 / 60)
            if player.grounded and player.y > 160:
                break

        self.assertTrue(player.grounded)
        self.assertEqual(player.y, 352)

    def test_player_uses_and_animates_the_horizontal_run_sheet(self):
        image = FakeCharacterImage()
        with patch('main_character.load_image', return_value=image) as load_image:
            player = MainCharacter()

        self.assertEqual(
            [Path(call.args[0]).name for call in load_image.call_args_list],
            ['mc_run.png', 'mc_jump_fall_land.png'],
        )

        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 0)

        player.pressed_keys.add(main_character.SDLK_d)
        player.update(0.1)
        player.update(0.03)
        player.draw()

        source_x, source_y, source_width, source_height = image.draw_calls[-1][:4]
        self.assertEqual(
            (source_x, source_y, source_width, source_height),
            (
                254 * (
                    player.RUN_FIRST_FRAME
                    + int(player.run_animation_time / player.RUN_FRAME_DURATION)
                    % (player.FRAME_COUNT - player.RUN_FIRST_FRAME)
                ),
                0,
                254,
                254,
            ),
        )
        self.assertEqual(image.draw_calls[-1][-2:], (96.0, 96.0))

        player.run_animation_time = 0.0
        run_frames = set()
        for _ in range(80):
            player.update(0.1)
            player.draw()
            run_frames.add(image.draw_calls[-1][0] // 254)
        self.assertEqual(run_frames, set(range(1, 8)))

    def test_run_speed_and_frame_rate_match_stride_length(self):
        run_image = FakeCharacterImage()
        air_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[run_image, air_image],
        ):
            player = MainCharacter(x=0, y=0, ground_y=0)

        player.pressed_keys.add(main_character.SDLK_d)
        stride_time = player.STRIDE_LENGTH_M / player.RUN_SPEED_MPS
        for _ in range(3):
            player.update(stride_time / 3)
        player.draw()

        expected_stride_pixels = (
            player.STRIDE_LENGTH_M * player.PIXELS_PER_METER
        )
        self.assertAlmostEqual(
            player.x,
            expected_stride_pixels,
            delta=player.MOVE_SPEED / 60,
        )
        self.assertEqual(
            run_image.draw_calls[-1][0] // player.FRAME_WIDTH,
            player.RUN_FIRST_FRAME,
        )

    def test_player_plays_jump_fall_and_land_animations(self):
        image = FakeCharacterImage()
        with patch('main_character.load_image', return_value=image):
            player = MainCharacter(x=0, y=0, ground_y=0)

        player.handle_event(SimpleNamespace(
            type=main_character.SDL_KEYDOWN,
            key=main_character.SDLK_SPACE,
        ))
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 254)

        player.update(0.1)
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 254)

        player.update(0.1)
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 508)

        player.update(0.1)
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 762)

        while player.state != 'FALL':
            player.update(1 / 60)
        player.y = 500
        player.velocity_y = 0
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 4 * 254)

        fall_frames = []
        for _ in range(4):
            player.update(0.1)
            player.draw()
            fall_frames.append(image.draw_calls[-1][0])
        self.assertEqual(fall_frames, [4 * 254, 5 * 254, 6 * 254, 4 * 254])

        while not player.grounded:
            player.update(1 / 60)
        self.assertEqual(player.state, 'LAND')
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 7 * 254)

        player.update(0.1)
        player.update(0.1)
        player.update(0.1)
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 9 * 254)

        while player.state == 'LAND':
            player.update(0.1)
        player.draw()
        self.assertEqual(image.draw_calls[-1][0], 0)

    def test_player_skips_land_animation_when_landing_while_running(self):
        run_image = FakeCharacterImage()
        air_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[run_image, air_image],
        ):
            player = MainCharacter(x=0, y=0, ground_y=0)

        player.grounded = False
        player.velocity_y = -1
        player.state = 'FALL'
        player.pressed_keys.add(main_character.SDLK_d)
        player.update(0.01)

        self.assertTrue(player.grounded)
        self.assertEqual(player.state, 'RUN')
        player.draw()
        self.assertEqual(len(run_image.draw_calls), 1)
        self.assertEqual(len(air_image.draw_calls), 0)

    def test_player_interrupts_land_animation_when_run_starts(self):
        run_image = FakeCharacterImage()
        air_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[run_image, air_image],
        ):
            player = MainCharacter(x=0, y=0, ground_y=0)

        player.state = 'LAND'
        player.animation_time = player.FRAME_DURATION
        player.draw()
        self.assertEqual(len(air_image.draw_calls), 1)

        player.pressed_keys.add(main_character.SDLK_d)
        player.update(1 / 60)
        player.draw()

        self.assertEqual(player.state, 'RUN')
        self.assertEqual(player.run_animation_time, 1 / 60)
        self.assertEqual(run_image.draw_calls[-1][0], player.FRAME_WIDTH)
        self.assertEqual(len(air_image.draw_calls), 1)

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
