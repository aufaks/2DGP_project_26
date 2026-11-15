class ActionRecorder:
    def __init__(self, max_duration_seconds=10.0, fixed_dt=1 / 60):
        if max_duration_seconds <= 0 or fixed_dt <= 0:
            raise ValueError('Recording duration and fixed timestep must be positive.')

        self.is_recording = False
        self.start_pose = None
        self.frames = []
        self.max_frames = max(1, int(round(max_duration_seconds / fixed_dt)))

    @property
    def has_recording(self):
        return bool(self.frames) and not self.is_recording

    def start(self, actor):
        self.start_pose = actor.capture_pose()
        self.frames = []
        self.is_recording = True

    def reset(self):
        self.is_recording = False
        self.start_pose = None
        self.frames = []

    def stop(self):
        if not self.is_recording:
            return None

        self.is_recording = False
        return self.start_pose

    def record(self, command):
        if not self.is_recording:
            return False

        self.frames.append(command)
        if len(self.frames) >= self.max_frames:
            self.stop()
            return True
        return False
