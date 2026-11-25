import math


class GameOverEffect:
    def shake_offset(self, elapsed):
        duration = .26
        t = max(0.0, elapsed)
        if t >= duration:
            return 0.0, 0.0
        fade = (1 - t / duration) ** 2
        return (5.0 * fade * math.sin(76 * t),
                4.0 * fade * math.sin(91 * t + 0.8))

    def draw(self, width, height, elapsed, edge_effect):
        t = max(0.0, elapsed)
        impact = max(0.0, 1 - t / .28)
        glow = .30 + .60 * impact
        edge_effect.draw(width, height, (255, 105, 123), glow)
