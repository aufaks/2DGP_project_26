import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pico2d import (
    SDL_KEYDOWN, SDL_MOUSEBUTTONDOWN, SDLK_DOWN, SDLK_ESCAPE, SDLK_RETURN,
)

import game_world
import main
from pause_menu import PauseMenu


class PauseMenuTests(unittest.TestCase):
    @staticmethod
    def key(key):
        return SimpleNamespace(type=SDL_KEYDOWN, key=key)

    @staticmethod
    def click(x, y):
        return SimpleNamespace(
            type=SDL_MOUSEBUTTONDOWN,
            button=1,
            x=x,
            y=PauseMenu.HEIGHT - y,
        )

    def setUp(self):
        self.menu = PauseMenu.__new__(PauseMenu)
        self.menu.selected = 0
        main.hold_key_tracker.reset()
        main.hotkey_keys_down.clear()
        self.addCleanup(main.hold_key_tracker.reset)
        self.addCleanup(main.hotkey_keys_down.clear)

    def test_keyboard_navigation_and_escape(self):
        self.assertIsNone(self.menu.handle_event(self.key(SDLK_DOWN)))
        self.assertEqual(self.menu.handle_event(self.key(SDLK_RETURN)), 'restart')
        self.assertIsNone(self.menu.handle_event(self.key(SDLK_DOWN)))
        self.assertEqual(self.menu.handle_event(self.key(SDLK_RETURN)), 'title')
        self.assertEqual(self.menu.handle_event(self.key(SDLK_ESCAPE)), 'continue')

    def test_mouse_selects_and_activates_button(self):
        bottom = PauseMenu.BUTTON_BOTTOMS[2]
        x = (PauseMenu.BUTTON_LEFT + PauseMenu.BUTTON_RIGHT) // 2
        y = bottom + PauseMenu.BUTTON_HEIGHT // 2
        self.assertEqual(self.menu.handle_event(self.click(x, y)), 'title')

    def test_escape_pauses_and_clears_held_player_input(self):
        actor = SimpleNamespace(
            pressed_keys={1},
            _pending_command=object(),
            _jump_pressed=True,
        )
        menu = SimpleNamespace(selected=2)
        with patch.object(main, 'player', actor), \
                patch.object(main, 'active_echo', None), \
                patch.object(main, 'recording_echo', None), \
                patch.object(main, 'pause_menu', menu), \
                patch.object(main, 'screen', 'game'), \
                patch.object(
                    main,
                    'get_events',
                    return_value=[self.key(SDLK_ESCAPE)],
                ):
            main.handle_events()

            self.assertEqual(main.screen, 'pause')
            self.assertEqual(menu.selected, 0)
            self.assertFalse(actor.pressed_keys)
            self.assertIsNone(actor._pending_command)
            self.assertFalse(actor._jump_pressed)

    def test_pause_actions_continue_restart_or_open_title(self):
        for action, expected_screen in (
            ('continue', 'game'),
            ('restart', 'game'),
            ('title', 'title'),
        ):
            menu = SimpleNamespace(handle_event=Mock(return_value=action))
            with self.subTest(action=action), \
                    patch.object(main, 'pause_menu', menu), \
                    patch.object(main, 'screen', 'pause'), \
                    patch.object(
                        main,
                        'get_events',
                        return_value=[self.key(SDLK_RETURN)],
                    ), \
                    patch.object(main, 'reset_world') as reset_world:
                main.handle_events()
                self.assertEqual(main.screen, expected_screen)
                if action == 'restart':
                    reset_world.assert_called_once_with()
                else:
                    reset_world.assert_not_called()

    def test_world_does_not_update_while_paused(self):
        with patch.object(main, 'screen', 'pause'), \
                patch.object(game_world, 'update') as update:
            main.update_world(1 / 60)
            update.assert_not_called()

    def test_pause_screen_renders_scene_and_menu(self):
        menu = SimpleNamespace(draw=Mock())
        with patch.object(main, 'screen', 'pause'), \
                patch.object(main, 'pause_menu', menu), \
                patch.object(main, 'clear_canvas'), \
                patch.object(main, 'update_canvas'), \
                patch.object(game_world, 'render') as render:
            main.render_world()
            render.assert_called_once_with(main.camera)
            menu.draw.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
