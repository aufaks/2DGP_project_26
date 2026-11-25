import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from echo_slot_ui import EchoSlotUI


class EchoSlotUiTests(unittest.TestCase):
    def test_recording_playback_and_empty_states(self):
        ui = EchoSlotUI.__new__(EchoSlotUI)
        ui.draw_slot = Mock()
        recorder = SimpleNamespace(is_recording=True, progress=.4,
                                   has_recording=False)
        ui.draw(recorder, None)
        ui.draw_slot.assert_any_call(0, filled=False, progress=.4)
        recorder.is_recording = False
        recorder.has_recording = True
        ui.draw_slot.reset_mock()
        ui.draw(recorder, SimpleNamespace(progress=.7))
        ui.draw_slot.assert_any_call(0, filled=True, progress=.7)
        ui.draw_slot.assert_any_call(1)
        ui.draw_slot.assert_any_call(2)
        ui.draw_slot.reset_mock()
        ui.draw(recorder, None)
        ui.draw_slot.assert_any_call(0, filled=True)
