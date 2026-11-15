import unittest
from unittest.mock import patch

from recording_effect import draw_recording_effect


class RecordingEffectTests(unittest.TestCase):
    def test_draws_a_thin_transparent_blue_gradient_and_restores_blending(self):
        with patch(
            'recording_effect._renderer',
            return_value=object(),
        ), patch(
            'recording_effect.pico2d.SDL_GetRenderDrawBlendMode',
            return_value=0,
        ), patch(
            'recording_effect.pico2d.SDL_SetRenderDrawBlendMode',
            return_value=0,
        ) as set_blend_mode, patch(
            'recording_effect.draw_rectangle',
        ) as draw_rectangle:
            draw_recording_effect(800, 576)

        calls = draw_rectangle.call_args_list
        self.assertEqual(len(calls), 16 * 4)
        self.assertEqual(calls[0].args[:4], (0, 0, 800, 1))
        alphas = [calls[band * 4].args[7] for band in range(16)]
        self.assertEqual((alphas[0], alphas[-1]), (150, 0))
        self.assertTrue(
            all(outer >= inner for outer, inner in zip(alphas, alphas[1:]))
        )
        self.assertEqual(calls[0].kwargs['filled'], True)
        self.assertEqual(
            set_blend_mode.call_args_list[-1].args[1],
            0,
        )


if __name__ == '__main__':
    unittest.main()
