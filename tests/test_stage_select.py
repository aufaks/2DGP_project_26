import unittest
from unittest.mock import patch

from pico2d import SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDLK_ESCAPE, SDLK_RETURN

from stage_select import StageSelect


class StageSelectTests(unittest.TestCase):
    def setUp(self):
        # Input handling does not require a window or loaded artwork.
        self.menu = StageSelect.__new__(StageSelect)
        self.menu.show_worlds()
        self.menu.world = 1

    @staticmethod
    def key(key):
        return type('Event', (), {'type': SDL_KEYDOWN, 'key': key})()

    @staticmethod
    def click(x, y):
        return type('Event', (), {
            'type': SDL_MOUSEBUTTONDOWN, 'button': 1, 'x': x, 'y': 720 - y,
        })()

    def test_world_selection_and_back_navigation(self):
        self.menu.handle_event(self.click(1100, 340))
        self.assertEqual((self.menu.mode, self.menu.world), ('stages', 4))
        self.assertIsNone(self.menu.handle_event(self.key(SDLK_RETURN)))
        self.menu.handle_event(self.key(SDLK_ESCAPE))
        self.assertEqual(self.menu.mode, 'world')
        self.assertEqual(self.menu.handle_event(self.key(SDLK_ESCAPE)), ('title',))

    def test_only_existing_stages_can_start(self):
        self.menu.show_stages(1)
        self.assertIsNone(self.menu.handle_event(self.click(80, 340)))
        self.assertEqual(self.menu.stage, 4)
        self.assertIsNone(self.menu.handle_event(self.key(SDLK_RETURN)))
        self.assertEqual(self.menu.handle_event(self.click(180, 450)), ('play', 1, 2))
        self.assertEqual(self.menu.handle_event(self.click(295, 450)), ('play', 1, 3))
        self.assertEqual(self.menu.handle_event(self.click(80, 450)), ('play', 1, 1))

    def test_main_enters_selection_before_loading_a_stage(self):
        import main

        previous = (main.screen, main.title_screen, main.stage_select)
        try:
            main.screen = 'title'
            main.title_screen = type('Title', (), {
                'handle_event': lambda self, event: 'start',
            })()
            main.stage_select = self.menu
            with patch.object(main, 'get_events', return_value=[self.key(SDLK_RETURN)]), \
                    patch.object(main, 'reset_world') as reset:
                main.handle_events()
                self.assertEqual(main.screen, 'select')
                reset.assert_not_called()
            self.menu.show_stages(1)
            with patch.object(main, 'get_events', return_value=[self.click(80, 450)]), \
                    patch.object(main, 'reset_world') as reset:
                main.handle_events()
                self.assertEqual((main.screen, main.world_number, main.stage_number),
                                 ('stage_entry', 1, 1))
                reset.assert_called_once_with()
        finally:
            main.screen, main.title_screen, main.stage_select = previous


if __name__ == '__main__':
    unittest.main()
