import unittest
from unittest.mock import Mock

from hold_action_effect import draw_hold_action_effect
from recording_effect import draw_recording_effect


class ScreenEdgeEffectTests(unittest.TestCase):
    def test_recording_is_blue(self):
        effect = Mock()
        draw_recording_effect(1280, 720, effect)
        effect.draw.assert_called_once_with(1280, 720, (95, 168, 255), .72)

    def test_save_and_restore_fade_and_expire(self):
        effect = Mock()
        draw_hold_action_effect(1280, 720, 'save', 0, effect)
        effect.draw.assert_called_once_with(1280, 720, (85, 255, 151), .9)
        effect.reset_mock()
        draw_hold_action_effect(1280, 720, 'restore', .325, effect)
        effect.draw.assert_called_once_with(1280, 720, (255, 180, 72), .45)
        effect.reset_mock()
        draw_hold_action_effect(1280, 720, 'save', .65, effect)
        effect.draw.assert_not_called()

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            draw_hold_action_effect(1280, 720, 'other', 0, Mock())
