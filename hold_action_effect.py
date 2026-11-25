_DURATION = 0.65
_COLORS = {
    'save': (85, 255, 151),
    'restore': (255, 180, 72),
}


def draw_hold_action_effect(width, height, action, elapsed, effect):
    if action not in _COLORS:
        raise ValueError('Action must be "save" or "restore".')
    if elapsed < 0 or elapsed >= _DURATION:
        return
    effect.draw(width, height, _COLORS[action], .90 * (1 - elapsed / _DURATION))
