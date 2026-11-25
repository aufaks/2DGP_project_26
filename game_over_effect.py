class GameOverEffect:
    def draw(self, width, height, elapsed, edge_effect):
        edge_effect.draw(width, height, (255, 75, 83),
                         .85 * min(max(elapsed, 0) / 0.15, 1))
