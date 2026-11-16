class HoldKeyTracker:
    def __init__(self, hold_seconds=2.0):
        if hold_seconds <= 0:
            raise ValueError('Hold duration must be positive.')

        self.hold_seconds = hold_seconds
        self._started_at = {}
        self._triggered = set()

    def key_down(self, key, timestamp):
        if key not in self._started_at:
            self._started_at[key] = timestamp

    def key_up(self, key):
        self._started_at.pop(key, None)
        self._triggered.discard(key)

    def ready_keys(self, timestamp):
        ready = []
        for key, started_at in self._started_at.items():
            if (
                key not in self._triggered
                and timestamp - started_at >= self.hold_seconds
            ):
                ready.append(key)
                self._triggered.add(key)
        return ready

    def reset(self):
        self._started_at.clear()
        self._triggered.clear()
