import unittest
from types import SimpleNamespace
from unittest.mock import patch

from echo_slot_ui import draw_echo_slot_ui


class FakeFont:
    def __init__(self):
        self.drawn_text = []

    def draw(self, x, y, text, color):
        self.drawn_text.append(text)


class EchoSlotUiTests(unittest.TestCase):
    def test_recording_shows_remaining_time_and_bottom_up_progress(self):
        recorder = SimpleNamespace(
            is_recording=True,
            progress=0.5,
            remaining_seconds=5.0,
            has_recording=False,
            recorded_seconds=0.0,
        )
        font = FakeFont()

        with patch('echo_slot_ui.draw_rectangle') as draw_rectangle:
            draw_echo_slot_ui(recorder, None, font)

        self.assertEqual(draw_rectangle.call_args_list[0].args[:4], (12, 12, 212, 100))
        self.assertIn('I/J', font.drawn_text)
        self.assertIn('O/K', font.drawn_text)
        self.assertIn('P/L', font.drawn_text)
        self.assertIn('5.0s', font.drawn_text)
        self.assertEqual(font.drawn_text.count('잠김'), 2)
        fill = draw_rectangle.call_args_list[2].args
        self.assertEqual(fill[1], 43)
        self.assertEqual(fill[3], 63)

    def test_playback_shows_remaining_time(self):
        recorder = SimpleNamespace(
            is_recording=False,
            has_recording=True,
            recorded_seconds=5.0,
        )
        echo = SimpleNamespace(
            progress=0.25,
            remaining_seconds=3.75,
        )
        font = FakeFont()

        with patch('echo_slot_ui.draw_rectangle'):
            draw_echo_slot_ui(recorder, echo, font)

        self.assertIn('I/J', font.drawn_text)
        self.assertIn('3.8s', font.drawn_text)


if __name__ == '__main__':
    unittest.main()
