import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from echo_slot_ui import EchoSlotUI


class EchoSlotUiTests(unittest.TestCase):
    def test_particles_only_for_saved_slots(self):
        ui = EchoSlotUI.__new__(EchoSlotUI)
        ui.base = Mock()
        ui.fill = Mock()
        ui.key_bg = Mock()
        ui.recording_icon = Mock()
        ui.keys = {key: Mock() for key in ui.RECORD_KEYS + ui.PLAY_KEYS}
        ui.draw_particles = Mock()
        ui._tinted = Mock()
        ui.draw_slot(0)
        ui.draw_slot(1, recording=True)
        ui.draw_particles.assert_not_called()
        ui.draw_slot(2, filled=True)
        ui.draw_particles.assert_called_once_with(2)

    def test_recording_playback_and_empty_states(self):
        ui = EchoSlotUI.__new__(EchoSlotUI)
        ui.panel = Mock()
        ui.draw_slot = Mock()
        recorder = SimpleNamespace(is_recording=True, progress=.4,
                                   has_recording=False)
        ui.draw(recorder, None, world_number=3)
        ui.draw_slot.assert_any_call(0, progress=.4, recording=True)
        recorder.is_recording = False
        recorder.has_recording = True
        ui.draw_slot.reset_mock()
        ui.draw(recorder, SimpleNamespace(progress=.7), world_number=3)
        ui.draw_slot.assert_any_call(0, filled=True, progress=.7)
        ui.draw_slot.assert_any_call(1)
        ui.draw_slot.assert_any_call(2)
        ui.draw_slot.reset_mock()
        ui.draw(recorder, None, world_number=3)
        ui.draw_slot.assert_any_call(0, filled=True)

    def test_first_two_worlds_draw_one_slot_and_compact_panel(self):
        recorder = SimpleNamespace(is_recording=False, has_recording=False)
        for world_number in (1, 2):
            with self.subTest(world_number=world_number):
                ui = EchoSlotUI.__new__(EchoSlotUI)
                ui.panel = Mock()
                ui.draw_slot = Mock()
                ui.draw(recorder, None, world_number=world_number)
                ui.draw_slot.assert_called_once_with(0, filled=False)
                ui.panel.draw.assert_called_once_with(62, 64, 108, 106)
