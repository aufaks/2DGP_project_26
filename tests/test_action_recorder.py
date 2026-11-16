import unittest
from pathlib import Path
from unittest.mock import patch

import main_character
from action_recorder import ActionRecorder
from echo_character import EchoCharacter
from game_commands import PlayerCommand
from main_character import MainCharacter
from tiled_map import TiledMap


class FakeImage:
    w = 128
    h = 32

    def clip_composite_draw(self, *args):
        pass


class ActionRecorderTests(unittest.TestCase):
    def setUp(self):
        self.character_image = patch(
            'main_character.load_image',
            return_value=FakeImage(),
        )
        self.character_image.start()
        self.addCleanup(self.character_image.stop)

    def test_records_commands_and_replaces_the_previous_recording(self):
        player = MainCharacter(x=100, y=0, ground_y=0)
        recorder = ActionRecorder()

        recorder.start(player)
        player.pressed_keys.add(main_character.SDLK_d)
        command = player.command_for_tick()
        recorder.record(command)
        player.update(1 / 60)
        self.assertEqual(recorder.stop(), recorder.start_pose)

        self.assertTrue(recorder.has_recording)
        self.assertEqual(recorder.start_pose.x, 100)
        self.assertEqual(recorder.frames, [PlayerCommand(move_x=1)])

        recorder.start(player)
        self.assertFalse(recorder.has_recording)
        recorder.stop()
        self.assertFalse(recorder.has_recording)

    def test_stops_recording_after_ten_seconds_at_sixty_hz(self):
        player = MainCharacter(x=100, y=0, ground_y=0)
        recorder = ActionRecorder()
        recorder.start(player)

        for _ in range(599):
            self.assertFalse(recorder.record(PlayerCommand(move_x=1)))

        self.assertTrue(recorder.record(PlayerCommand(move_x=1)))
        self.assertFalse(recorder.is_recording)
        self.assertEqual(len(recorder.frames), 600)

    def test_reports_recording_progress_and_remaining_time(self):
        player = MainCharacter(x=100, y=0, ground_y=0)
        recorder = ActionRecorder(max_duration_seconds=2.0)
        recorder.start(player)

        for _ in range(30):
            recorder.record(PlayerCommand())

        self.assertAlmostEqual(recorder.progress, 0.25)
        self.assertAlmostEqual(recorder.remaining_seconds, 1.5)
        self.assertAlmostEqual(recorder.recorded_seconds, 0.5)

    def test_restores_player_pose_and_clears_old_movement_input(self):
        player = MainCharacter(x=100, y=0, ground_y=0)
        start_pose = player.capture_pose()
        player.pressed_keys.add(main_character.SDLK_d)
        player.update(1 / 60)

        player.restore_pose(start_pose)

        self.assertEqual((player.x, player.y), (100, 0))
        self.assertTrue(player.grounded)
        self.assertFalse(player.pressed_keys)
        self.assertEqual(player.state, 'IDLE')

    def test_restores_only_the_saved_player_position(self):
        player = MainCharacter(x=100, y=0, ground_y=0)
        saved_position = player.capture_position()

        player.x = 250
        player.y = 120
        player.facing_left = True
        player.velocity_y = 300
        player.grounded = False

        player.restore_position(saved_position)

        self.assertEqual((player.x, player.y), saved_position)
        self.assertTrue(player.facing_left)
        self.assertEqual(player.velocity_y, 300)
        self.assertFalse(player.grounded)

    def test_echo_replays_the_same_commands_with_map_collisions(self):
        project_root = Path(__file__).resolve().parents[1]
        map_path = project_root / 'maps' / 'stage_01.tmj'
        map_image = patch('tiled_map.load_image', return_value=FakeImage())
        map_image.start()
        self.addCleanup(map_image.stop)
        tiled_map = TiledMap(map_path)

        player = MainCharacter(x=200, y=256, collision_map=tiled_map)
        frames = (
            [PlayerCommand(move_x=1, jump_pressed=True)]
            + [PlayerCommand(move_x=1)] * 71
        )
        echo = EchoCharacter(
            player.capture_pose(),
            frames,
            tiled_map,
            player.sprite_images,
        )

        self.assertAlmostEqual(echo.remaining_seconds, len(frames) / 60)
        for index, frame in enumerate(frames):
            player.update(1 / 60, frame)
            echo.update(1 / 60)
            if index == 0:
                self.assertAlmostEqual(echo.remaining_seconds, (len(frames) - 1) / 60)
                self.assertAlmostEqual(echo.progress, 1 / len(frames))

        self.assertTrue(echo.finished)
        self.assertEqual(echo.frame_index, len(frames))
        self.assertEqual(echo.remaining_seconds, 0)
        self.assertEqual(echo.progress, 1)
        self.assertEqual((echo.x, echo.y), (player.x, player.y))
        self.assertEqual(echo.grounded, player.grounded)
        self.assertEqual(echo.facing_left, player.facing_left)


if __name__ == '__main__':
    unittest.main()
