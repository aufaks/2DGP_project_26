import math

from sdl2 import (
    SDL_BLENDMODE_ADD, SDL_BLENDMODE_BLEND, SDL_SetTextureAlphaMod,
    SDL_SetTextureBlendMode, SDL_SetTextureColorMod,
)

from main_character import MainCharacter


class EchoCharacter(MainCharacter):
    # I/J, O/K, P/L: the same animation frames, three distinct echoes.
    PALETTE = ((78, 184, 255), (86, 240, 166), (198, 139, 255))

    def __init__(
        self,
        start_pose,
        frames,
        collision_map,
        sprite_images,
        fixed_dt=1 / 60,
        palette_index=0,
        recording=False,
    ):
        if fixed_dt <= 0:
            raise ValueError('Fixed timestep must be positive.')
        if not 0 <= palette_index < len(self.PALETTE):
            raise ValueError('Echo palette index must be 0, 1, or 2.')

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
        self.recording = recording
        self.finished = not self.frames and not recording
        self.fixed_dt = float(fixed_dt)
        self.palette_index = palette_index

    def draw(self, camera=None):
        image = (self.run_image if self.state == 'RUN' else
                 self.idle_image if self.state == 'IDLE' else self.air_image)
        texture = image.texture
        color = self.PALETTE[self.palette_index]
        original_size = self.DRAW_SIZE

        try:
            SDL_SetTextureColorMod(texture, *color)
            SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_ADD)
            SDL_SetTextureAlphaMod(texture, 72)
            self.DRAW_SIZE = original_size * 1.10
            super().draw(camera)

            # Translucency makes the environment visible through the echo.
            self.DRAW_SIZE = original_size
            SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_BLEND)
            pulse = (math.sin(self.animation_time * 9.0) + 1.0) / 2.0
            SDL_SetTextureAlphaMod(texture, int(165 + 27 * pulse))
            super().draw(camera)
        finally:
            self.DRAW_SIZE = original_size
            SDL_SetTextureColorMod(texture, 255, 255, 255)
            SDL_SetTextureAlphaMod(texture, 255)
            SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_BLEND)

    @property
    def progress(self):
        if not self.frames:
            return 1.0
        return min(1.0, self.frame_index / len(self.frames))

    @property
    def remaining_seconds(self):
        remaining_frames = max(0, len(self.frames) - self.frame_index)
        return remaining_frames * self.fixed_dt

    def update(self, dt=1 / 60):
        if self.recording:
            MainCharacter.update(self, dt)
            return
        if self.finished:
            return

        command = self.frames[self.frame_index]
        super().update(dt, command)
        self.frame_index += 1
        self.finished = self.frame_index >= len(self.frames)
