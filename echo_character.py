from main_character import MainCharacter


class EchoCharacter(MainCharacter):
    def __init__(self, start_pose, frames, collision_map, sprite_images):
        super().__init__(
            x=start_pose.x,
            y=start_pose.y,
            collision_map=collision_map,
            sprite_images=sprite_images,
        )
        self.facing_left = start_pose.facing_left
        self.velocity_y = start_pose.velocity_y
        self.grounded = start_pose.grounded
        self.state = (
            'IDLE' if self.grounded
            else 'JUMP' if self.velocity_y > 0
            else 'FALL'
        )
        self.frames = tuple(frames)
        self.frame_index = 0
        self.finished = not self.frames

    def update(self, dt=1 / 60):
        if self.finished:
            return

        command = self.frames[self.frame_index]
        super().update(dt, command)
        self.frame_index += 1
        self.finished = self.frame_index >= len(self.frames)
