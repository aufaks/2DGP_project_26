import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stage_map import StageMap
from stage_progress import next_stage, stage_path


class StageMapTests(unittest.TestCase):
    def test_stage_loads_and_has_ground(self):
        with patch('stage_map.load_image'):
            stage = StageMap(stage_path(1, 1))
        self.assertEqual((stage.pixel_width, stage.pixel_height), (1280, 720))
        self.assertEqual(stage.player_spawn, (120, 136))
        self.assertTrue(stage.is_supported(120, 136, 36))
        self.assertTrue(stage.echo_unlocked)
        self.assertEqual(next_stage(1, 9), (2, 1))
        self.assertIsNone(next_stage(3, 9))

    def test_custom_objects_and_slopes(self):
        data = {
            'size': [1280, 720],
            'background': 'back.png',
            'player_spawn': [96, 160],
            'collision_rects': [[0, 0, 1280, 160]],
            'slopes': [[320, 160, 352, 192, 'SlopeUpRight']],
            'images': [],
            'objects': [
                {'id': 'gate', 'type': 'Door', 'rect': [600, 160, 640, 320]},
                {'id': 'sensor', 'type': 'PressurePlate',
                 'target_id': 'gate', 'rect': [250, 148, 310, 160]},
                {'id': 'device', 'type': 'EchoDevice',
                 'rect': [90, 160, 130, 200]},
                {'id': 'exit', 'type': 'StageExit',
                 'rect': [1100, 160, 1200, 260]},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stage.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            with patch('stage_map.load_image'):
                stage = StageMap(path)
        self.assertFalse(stage.echo_unlocked)
        self.assertEqual(stage._slope_surface_at(336), 176)
        self.assertEqual(len(stage.stage_exits), 1)
        self.assertIn(stage.doors['gate'].rect, stage.solid_rects)


if __name__ == '__main__':
    unittest.main()
