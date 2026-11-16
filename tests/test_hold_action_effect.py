import unittest
from unittest.mock import patch

from hold_action_effect import draw_hold_action_effect


class HoldActionEffectTests(unittest.TestCase):
    def test_draws_fading_green_border_for_save(self):
        self.assert_draws_border('save', 0.0, (70, 235, 135), 220)

    def test_draws_fading_orange_border_for_restore(self):
        self.assert_draws_border('restore', 0.325, (255, 170, 55), 110)

    def test_does_not_draw_after_effect_expires(self):
        with patch('hold_action_effect.draw_rectangle') as draw_rectangle:
            draw_hold_action_effect(800, 576, 'save', 0.65)

        draw_rectangle.assert_not_called()

    def assert_draws_border(self, action, elapsed, color, alpha):
        with patch(
            'hold_action_effect._renderer',
            return_value=object(),
        ), patch(
            'hold_action_effect.pico2d.SDL_GetRenderDrawBlendMode',
            return_value=0,
        ), patch(
            'hold_action_effect.pico2d.SDL_SetRenderDrawBlendMode',
            return_value=0,
        ) as set_blend_mode, patch(
            'hold_action_effect.draw_rectangle',
        ) as draw_rectangle:
            draw_hold_action_effect(800, 576, action, elapsed)

        calls = draw_rectangle.call_args_list
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[0].args, (0, 0, 800, 12, *color, alpha))
        self.assertTrue(all(call.kwargs['filled'] for call in calls))
        self.assertEqual(set_blend_mode.call_args_list[-1].args[1], 0)


if __name__ == '__main__':
    unittest.main()
