import unittest

from hold_key_tracker import HoldKeyTracker


class HoldKeyTrackerTests(unittest.TestCase):
    def test_key_triggers_once_after_the_full_hold_duration(self):
        tracker = HoldKeyTracker(hold_seconds=2.0)
        tracker.key_down('save', 10.0)

        self.assertEqual(tracker.ready_keys(11.99), [])
        self.assertEqual(tracker.ready_keys(12.0), ['save'])
        self.assertEqual(tracker.ready_keys(12.5), [])

    def test_releasing_and_pressing_again_starts_a_new_hold(self):
        tracker = HoldKeyTracker(hold_seconds=2.0)
        tracker.key_down('restore', 10.0)
        tracker.key_up('restore')
        tracker.key_down('restore', 11.0)

        self.assertEqual(tracker.ready_keys(12.99), [])
        self.assertEqual(tracker.ready_keys(13.0), ['restore'])

    def test_repeated_keydown_does_not_restart_the_hold(self):
        tracker = HoldKeyTracker(hold_seconds=2.0)
        tracker.key_down('save', 10.0)
        tracker.key_down('save', 11.0)

        self.assertEqual(tracker.ready_keys(12.0), ['save'])


if __name__ == '__main__':
    unittest.main()
