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
        self.draw_rectangle = patch('game_objects.draw_rectangle')
        self.draw_rectangle.start()
        self.addCleanup(self.draw_rectangle.stop)

    def test_loads_starter_map_tiles_collision_and_spawn(self):
        tiled_map = TiledMap(self.map_path)

        self.assertEqual((tiled_map.width, tiled_map.height), (150, 50))
        self.assertEqual((tiled_map.pixel_width, tiled_map.pixel_height), (4800, 1600))
        self.assertEqual(
            [layer['name'] for layer, _ in tiled_map.tile_layers],
            ['Terrain'],
        )
        self.assertEqual(tiled_map.collision_rects, [(0, 0, 4800, 160)])
        self.assertIn(
            (1984, 1408, 2016, 1440),
            tiled_map.platform_rects,
        )
        self.assertNotIn(
            (256, 1408, 288, 1440),
            tiled_map.platform_rects,
        )
        self.assertEqual(tiled_map.player_spawn, (96, 160))
        self.assertEqual(set(tiled_map.doors), {'exit'})
        self.assertEqual(len(tiled_map.pressure_plates), 1)
        self.assertEqual(tiled_map.pressure_plates[0].target_id, 'exit')
        self.assertEqual(tiled_map.doors['exit'].rect, (1568, 640, 1600, 800))
        self.assertEqual(
            tiled_map.pressure_plates[0].rect,
            (1024, 1396, 1120, 1408),
        )

        terrain = tiled_map.tile_layers[0][1]
        tile_types = {
            tileset['firstgid'] + tile['id']:
                tile.get('class') or tile.get('type')
            for tileset in tiled_map.tilesets
            for tile in tileset.get('tiles', [])
        }
        self.assertFalse(any(
            tile_types.get(gid & 0x0FFFFFFF) == 'Sky'
            for gid in terrain
        ))
        self.assertTrue(tiled_map.is_supported(4000, 160, 36))
        self.assertTrue(tiled_map.is_supported(1984, 1440, 36))
        self.assertTrue(tiled_map.is_supported(840, 256, 36))

    def test_pressure_plate_opens_its_linked_door_for_player_and_echo(self):
        tiled_map = TiledMap(self.map_path)
        door = tiled_map.doors['exit']
        actor = SimpleNamespace(
            x=848,
            y=160,
            grounded=True,
            get_collision_box=lambda: (830, 160, 866, 220),
        )

        tiled_map.update_mechanisms([actor])
        self.assertTrue(tiled_map.pressure_plates[0].is_pressed)
        self.assertTrue(door.is_open)
        self.assertNotIn(door.rect, tiled_map.solid_rects)

        actor.x = 980
        actor.y = 160
        actor.get_collision_box = lambda: (962, 160, 998, 220)
        tiled_map.update_mechanisms([actor])
        self.assertFalse(tiled_map.pressure_plates[0].is_pressed)
        self.assertTrue(door.is_open)

        actor.x = 1040
        actor.get_collision_box = lambda: (1022, 160, 1058, 220)
        tiled_map.update_mechanisms([actor])
        self.assertFalse(door.is_open)
        self.assertIn(door.rect, tiled_map.solid_rects)

    def test_closed_door_blocks_actor_and_plate_requires_grounded_actor(self):
        tiled_map = TiledMap(self.map_path)
        x, _, _, _ = tiled_map.move_actor(900, 160, 36, 60, 100, 0)
        self.assertEqual(x, 942)

        actor = SimpleNamespace(
            x=848,
            y=160,
            grounded=False,
            get_collision_box=lambda: (830, 160, 866, 220),
        )
        tiled_map.update_mechanisms([actor])
        self.assertFalse(tiled_map.pressure_plates[0].is_pressed)
        self.assertFalse(tiled_map.doors['exit'].is_open)

    def _make_collision_test_map(self):
        tiled_map = object.__new__(TiledMap)
        tiled_map.tile_width = 32
        tiled_map.tile_height = 32
        tiled_map.pixel_width = 128
        tiled_map.pixel_height = 64
        tiled_map.collision_rects = []
        tiled_map.platform_rects = []
        tiled_map.slope_tiles = []
        tiled_map.doors = {}
        tiled_map.tilesets = [{
            'firstgid': 1,
            'tiles': [
                {'id': 0, 'type': 'Grass'},
                {'id': 1, 'type': 'Dirt'},
                {'id': 2, 'type': 'Stone'},
                {'id': 3, 'type': 'Sky'},
                {'id': 4, 'type': 'SlopeUpRight'},
                {'id': 5, 'type': 'SlopeUpLeft'},
                {'id': 6, 'class': 'Sky'},
            ],
        }]
        tiled_map.tile_layers = [(
            {'name': 'Background', 'width': 4, 'height': 2},
            [1, 2, 5, 6, 5, 4, 4, 0],
        ), (
            {'name': 'Terrain', 'width': 4, 'height': 2},
            [0, 4, 0, 0, 0, 0, 3, 7],
        )]
        tiled_map._load_platform_tile_collisions()
        return tiled_map

    def test_every_non_sky_tile_collides_individually_on_any_layer(self):
        tiled_map = self._make_collision_test_map()

        self.assertEqual(tiled_map.platform_rects, [
            (0, 32, 32, 64),
            (64, 0, 96, 32),
        ])
        self.assertEqual(tiled_map.slope_tiles, [
            (64, 32, 96, 64, 'SlopeUpRight'),
            (96, 32, 128, 64, 'SlopeUpLeft'),
            (0, 0, 32, 32, 'SlopeUpRight'),
        ])

        _, y, _, hit_ceiling = tiled_map.move_actor(16, 20, 8, 8, 0, 10)
        self.assertEqual(y, 24)
        self.assertTrue(hit_ceiling)

        _, right_y, right_grounded, _ = tiled_map.move_actor(
            8, 8, 8, 8, 8, 0
        )
        _, left_y, left_grounded, _ = tiled_map.move_actor(
            104, 56, 8, 8, 8, 0
        )
        self.assertEqual(right_y, 16)
        self.assertTrue(right_grounded)
        self.assertEqual(left_y, 48)
        self.assertTrue(left_grounded)

    def _add_slope_tile(self, tiled_map, gid, column=20, row=20):
        terrain_layer, terrain = next(
            (layer, values)
            for layer, values in tiled_map.tile_layers
            if layer['name'] == 'Terrain'
        )
        terrain[row * terrain_layer['width'] + column] = gid
        tiled_map.platform_rects.clear()
        tiled_map.slope_tiles.clear()
        tiled_map._load_platform_tile_collisions()

    def test_slope_tiles_load_and_support_both_directions(self):
        tiled_map = TiledMap(self.map_path)
        self._add_slope_tile(tiled_map, 5)
        self._add_slope_tile(tiled_map, 6, column=25)

        self.assertIn(
            (640, 928, 672, 960, 'SlopeUpRight'),
            tiled_map.slope_tiles,
        )
        self.assertIn(
            (800, 928, 832, 960, 'SlopeUpLeft'),
            tiled_map.slope_tiles,
        )
        self.assertTrue(tiled_map.is_supported(644, 932, 36))
        self.assertTrue(tiled_map.is_supported(804, 956, 36))

        _, uphill_y, uphill_grounded, _ = tiled_map.move_actor(
            644, 932, 36, 60, 4, 0
        )
        _, downhill_y, downhill_grounded, _ = tiled_map.move_actor(
            804, 956, 36, 60, 4, 0
        )
        self.assertEqual(uphill_y, 936)
        self.assertTrue(uphill_grounded)
        self.assertEqual(downhill_y, 952)
        self.assertTrue(downhill_grounded)

    def test_actor_lands_on_slope_and_hits_its_underside(self):
        tiled_map = TiledMap(self.map_path)
        self._add_slope_tile(tiled_map, 5)

        _, y, grounded, hit_ceiling = tiled_map.move_actor(
            656, 980, 36, 60, 0, -50
        )
        self.assertEqual(y, 944)
        self.assertTrue(grounded)
        self.assertFalse(hit_ceiling)

        _, y, grounded, hit_ceiling = tiled_map.move_actor(
            656, 870, 36, 60, 0, 30
        )
        self.assertEqual(y, 884)
        self.assertFalse(grounded)
        self.assertTrue(hit_ceiling)

    def test_main_character_walks_up_slope(self):
        tiled_map = TiledMap(self.map_path)
        self._add_slope_tile(tiled_map, 5)
        with patch('main_character.load_image', return_value=FakeImage()):
            player = MainCharacter(x=644, y=932, collision_map=tiled_map)

        player.pressed_keys.add(main_character.SDLK_d)
        player.update(1 / 60)

        self.assertTrue(player.grounded)
        self.assertAlmostEqual(
            player.y,
            tiled_map._slope_surface_at(player.x),
        )
        self.assertGreater(player.y, 932)

    def test_horizontal_tile_flip_reverses_slope_collision(self):
        tiled_map = TiledMap(self.map_path)
        self._add_slope_tile(tiled_map, 0x80000000 | 5)

        self.assertIn(
            (640, 928, 672, 960, 'SlopeUpLeft'),
            tiled_map.slope_tiles,
        )

    def test_adjacent_slope_tiles_have_a_continuous_surface(self):
        tiled_map = TiledMap(self.map_path)
        terrain_layer, terrain = next(
            (layer, values)
            for layer, values in tiled_map.tile_layers
            if layer['name'] == 'Terrain'
        )
        terrain[20 * terrain_layer['width'] + 20] = 5
        terrain[19 * terrain_layer['width'] + 21] = 5
        tiled_map.platform_rects.clear()
        tiled_map.slope_tiles.clear()
        tiled_map._load_platform_tile_collisions()

        self.assertAlmostEqual(tiled_map._slope_surface_at(671.9), 959.9)
        self.assertEqual(tiled_map._slope_surface_at(672), 960)
        self.assertAlmostEqual(tiled_map._slope_surface_at(672.1), 960.1)

        x, y, grounded, _ = tiled_map.move_actor(
            668, 956, 36, 60, 4, 0
        )
        self.assertEqual((x, y), (672, 960))
        self.assertTrue(grounded)

    def test_actor_can_walk_from_slope_onto_higher_solid_tile(self):
        tiled_map = self._make_collision_test_map()
        _, values = tiled_map.tile_layers[0]
        values[:] = [0, 0, 0, 0, 5, 2, 0, 0]
        tiled_map.platform_rects.clear()
        tiled_map.slope_tiles.clear()
        tiled_map._load_platform_tile_collisions()

        x, y = 14, 14
        positions = []
        for _ in range(5):
            x, y, grounded, _ = tiled_map.move_actor(
                x, y, 36, 8, 4, 0
            )
            positions.append((x, y))
            self.assertTrue(grounded)

        self.assertEqual(
            positions,
            [(18, 18), (22, 22), (26, 26), (30, 30), (34, 32)],
        )

        tiled_map = self._make_collision_test_map()
        _, background = tiled_map.tile_layers[0]
        _, terrain = tiled_map.tile_layers[1]
        background[:] = [0, 0, 0, 0, 0, 0, 3, 6]
        terrain[:] = [0] * len(terrain)
        tiled_map.platform_rects.clear()
        tiled_map.slope_tiles.clear()
        tiled_map._load_platform_tile_collisions()

        x, y = 114, 14
        positions = []
        for _ in range(5):
            x, y, grounded, _ = tiled_map.move_actor(
                x, y, 36, 8, -4, 0
            )
            positions.append((x, y))
            self.assertTrue(grounded)

        self.assertEqual(
            positions,
            [(110, 18), (106, 22), (102, 26), (98, 30), (94, 32)],
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

        expected_draw_count = sum(
            sum(raw_gid != 0 for raw_gid in values)
            for _, values in tiled_map.tile_layers
        )
        self.assertEqual(draw_count, expected_draw_count)

    def test_camera_scales_and_centers_map_tiles(self):
        tiled_map = TiledMap(self.map_path)
        camera = Camera(800, 576, zoom=0.75)
        camera.follow(96, 160, tiled_map.pixel_width, tiled_map.pixel_height)
        image = tiled_map.tilesets[0]['image_object']
        draw_calls = []
        image.clip_composite_draw = lambda *args: draw_calls.append(args)

        tiled_map.draw()
        draw_calls.clear()
        tiled_map.draw(camera)

        expected_draw_count = sum(
            sum(raw_gid != 0 for raw_gid in values)
            for _, values in tiled_map.tile_layers
        )
        self.assertEqual(len(draw_calls), expected_draw_count)
        first_row = draw_calls[:tiled_map.width]
        for call in first_row:
            left = call[6] - call[-2] / 2
            right = call[6] + call[-2] / 2
            self.assertEqual(left, round(left))
            self.assertEqual(right, round(right))
        for previous, current in zip(first_row, first_row[1:]):
            self.assertEqual(
                previous[6] + previous[-2] / 2,
                current[6] - current[-2] / 2,
            )

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
            player = MainCharacter(x=200, y=256, collision_map=tiled_map)

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
            ['mc_run.png', 'mc_idle.png', 'mc_jump_fall_land.png'],
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
        idle_image = FakeCharacterImage()
        air_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[run_image, idle_image, air_image],
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

    def test_player_loops_six_idle_frames(self):
        idle_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[
                FakeCharacterImage(),
                idle_image,
                FakeCharacterImage(),
            ],
        ):
            player = MainCharacter()

        for frame_index in range(player.IDLE_FRAME_COUNT + 1):
            player.animation_time = frame_index * player.FRAME_DURATION
            player.draw()

        self.assertEqual(
            [call[0] for call in idle_image.draw_calls],
            [frame_index * player.FRAME_WIDTH for frame_index in range(6)]
            + [0],
        )

    def test_player_skips_land_animation_when_landing_while_running(self):
        run_image = FakeCharacterImage()
        idle_image = FakeCharacterImage()
        air_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[run_image, idle_image, air_image],
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
        idle_image = FakeCharacterImage()
        air_image = FakeCharacterImage()
        with patch(
            'main_character.load_image',
            side_effect=[run_image, idle_image, air_image],
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
